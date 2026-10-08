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
frenzy), with `--rescue` and the refreshed matrix. §12 (2026-09-25) is the delegated bank's overshoot under
standing wage pressure (`--wage-pressure`) and the three changes that answer it; §13 replaces independence's
crash and momentum bonus with inflation anchoring (`--bank-level`). §14 (2026-09-30) prices and shapes the five
directed-credit sectors apart (`--tune ai_dc_reserve=off`). §16 (2026-10-02) makes a slump pull inflation down
harder under an inflation target, and only there (`--tune pre_slump_pressure`). §17 (2026-10-05) makes a crash's tier a
ceiling, so a crash never raises the cycle. §18 (2026-10-05) stops the AI lifting a tool while the reason it bought
it still holds (`--tune pre_hold`). §19 (2026-10-05) makes the Bank Holiday stop the run and reopen with a
momentum bounce (`--holiday`, `--tune pre_holiday`). §20 (2026-10-05) traces §18's gold capital-controls
crashes to cells no AI runs and leaves the AI's weights alone (`--tune cc_cost=0`, `cc_damp=1`, `cc_weak=0`).
§21 (2026-10-05) measures Cooperative Ownership for the first time, with an interim arm posted on #720, and
retunes it. §22 adds a separate imported-crash population (`--imported-crash-years`); §23 makes command and cooperative arms permanent (`--economy`, `--hold-tools`, `--pool`). §24 (2026-10-05) measures the gold peg's deep-slump drain and ports `te_peg.1` (`--peg-slump`). §25 (2026-10-07) bounds the Emergency Liquidity Program to its crisis and ports its announcement (`--tune pre_eliq_bounds`, `--player-eliq`). Every table states which script it measured.

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
These clicks and crash rates are with every sector at 3 points; §14 re-measures them once the sectors are priced 1 to 4.

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

---

## 12. The delegated bank's overshoot (2026-09-25)

**Report.** Delegated central banks overcompensate in play: they set very high rates (around 15%), the
economy crashes, and the rate is still high long after. Nothing in §1–§11 showed this. A price-stability
dial peaked at about 10% a century and almost never reached the tight clamp. §1 even records "a steered dial
almost never reaches the clamp".

### Why the simulator never saw it

The simulator stubbed standing inflation pressure at zero. In game the labour laws grant
`country_wage_pressure_add` of +0.2 to +1.4pp (`common/laws/te_monetary_wage_pressure_injections.txt`), and
`te_mon_pressure_wage_spiral` counts it a second time above 8%. The price-stability rule is proportional
(`r̂* + π + 1.0 × (π − anchor) + lean`), so a standing pressure is met with a standing inflation error that the
rule then *doubles* into the nominal target. At +1pp, inflation settles near 3.6%. The target sits around 8%
before any lean, and the boom and bubble leans push it to 12–14%. The simulator now has `--wage-pressure`
(and `--deficit-mean`), plus six overshoot columns: each run's peak rate (median and p90), months at 10% or
more, months at a stance of +3 or tighter with the cycle below 40, downturns with no crash in the year before
("policy downturns"), and the mean stance over the year after a crash.

### F13 — The lean arrives as the boom breaks, and the rate cannot come back down

One run, fiat, price stability, +1pp wage pressure, as the script stood:

- **Months 0–28:** the target climbs 1 → 10 while the rate, drifting a third of a point a month, trails it.
  The stance stays *loose* for twenty months while inflation climbs, and bubble pressure goes 0 → 66.
- **Months 30–38:** boom. The phase lean (+1) and the bubble lean (+1) take the target to 12. The rate gets
  there in month 36, with the bubble at 82 and still climbing, and the stance hits the +4 clamp.
- **Month 40:** crash into panic. The target falls to 5 at once, but the rate is at 10.7 and can only come
  down a third of a point a month. The stance stays at +3 or tighter for about a year of panic, and the cycle
  sits at 0 for fourteen months.

Three things compound:

1. **The lean reads today's phase.** By the time the phase says "boom", the boom is nearly over.
2. **Cuts are as slow as hikes.** The drift is symmetric, so a crash finds the bank at the top of its hike
   and a year away from neutral.
3. **Standing pressure keeps π, and so the target, high** (F15 below; not fixed).

At +1pp the old script drove a fiat economy into downturn with no crash behind it 4.2 times a century, and
held a positive stance through the year after a crash (+1.0).

### F14 — Growth's half-weight reaction cannot hold the 8% wage-spiral edge

Growth ignores inflation below 4% and reacted at 0.5 above it. Under standing wage pressure that lets
inflation reach 8%. There the wage spiral doubles the pressure, and a +4 stance buys only −1.6pp against it.
At +1pp, fiat growth ran 8.7% mean inflation, a rate of 10% or more in 53% of months, 24% of months in
recession and a median longest slump of 295 months. That is worse than price stability on every count,
growth included. Every AI at war or with `scaled_debt ≥ 0.5` runs this mandate.

### What was tried

Measured with a scratch harness around the simulator (not committed): 120–150 runs, `--event-channel` on,
0 points, several wage/deficit settings.

| candidate | verdict |
|---|---|
| Inflation weight 1.0 → 0.5 | **Worse.** At +1pp, fiat price stability's p90 peak went 14 → 24, months ≥ 10% 10 → 27, recession 5 → 9%. A weaker reaction lets π climb and the nominal rate follows it. |
| Cap the desired real stance at +4 / +3 / +2.5 | +4 is a no-op. +3 and +2.5 cut slumps but let inflation escape under pressure: with +1pp wage and a 3% deficit, π99 went 9 → 40–48 and the median run's peak rate hit the 25% ceiling. |
| Cap the stance in a slump (+1 stagnation, 0 downturn, −1 panic) | The same trade, sharper. At +1pp, the growth mandate's π99 reached 48, the hyperinflation edge. |
| Growth → price stability above 5% core | Similar gains to the shipped reaction change, but the target jumps ~3pp at the switch, and under pressure it reversed direction 1.7–1.9× as often. |
| Outlook horizon 3 / 6 / 12 months | 12 is marginally better on slumps, but reverses the target up to a quarter more often than 6 (one ±1 random nudge is worth 7 cycle points of outlook). 3 is between the two. |
| Emergency cuts ×2 / ×3 / ×6, below 25 or 40, on today's value or the outlook | ×3 below 40 on today's value. ×6 adds little; below 25 misses stagnation; the outlook trigger measured the same. |

### What shipped

1. **The lean reads the cycle's outlook** — `te_mon_cycle_outlook` = value + 4.69 × momentum (six months at
   the 0.9 decay), clamped 0–100, on the same 88/75/25/10 edges. The bank stops leaning on a boom that is
   already turning and eases before the slump line is crossed.
2. **Emergency cuts** — `te_mon_drift_step_down`: a mandate-run bank (`te_mon_emergency_cuts`: delegated,
   AI or CBI) cuts at `te_mon_emergency_cut_factor` (3×) while the cycle is below 40. Hikes and the manual
   dial keep a third of a point a month. Scoping it to mandate-run banks is an **owner decision** (design §4).
3. **Growth reacts at full weight above 4%** — `te_mon_mandate_growth_reaction` 0.5 → 1.0. Growth is now
   price stability run 2.25pp warmer above the threshold, and unchanged below it.

`--tune pre_delegation_fix` restores all three. It reproduces the earlier simulator run for run.

### Result — 400 runs × 100 years per cell, `pre_delegation_fix` → shipped

**As the simulator stood (no wage pressure).** Recession months, policy downturns and the post-crash stance fall in every
price and growth cell. Crashes are flat or lower (gold growth +0.3–0.6, within noise), and peg defence is unchanged.

| cell | crashes | recession % | longest <40, mo | peak rate | p90 peak | rate ≥10 % | tight in slump % | policy downturns | post-crash stance | inflation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `commodity/price/0pt` | 9.7 → 9.6 | 8.6 → 6.8 | 36 → 32 | 6.0 → 6.0 | 6.0 → 6.0 | 0.0 → 0.0 | 0.04 → 0.01 | 0.6 → 0.3 | 0.01 → -0.64 | 0.09 → 0.10 |
| `gold/price/0pt` | 9.0 → 9.0 | 10.2 → 6.8 | 50 → 40 | 9.7 → 9.7 | 11.0 → 11.0 | 0.2 → 0.2 | 1.99 → 0.44 | 1.9 → 0.5 | 0.01 → -0.82 | 0.11 → 0.14 |
| `gold/price/5pt` | 5.6 → 4.9 | 4.1 → 2.0 | 39 → 32 | 9.0 → 9.0 | 10.0 → 10.0 | 0.1 → 0.1 | 1.58 → 0.48 | 1.6 → 0.3 | -0.32 → -0.97 | 0.12 → 0.12 |
| `fiat/price/0pt` | 9.9 → 8.5 | 8.9 → 5.5 | 29 → 26 | 10.0 → 10.0 | 11.7 → 12.0 | 1.3 → 1.2 | 0.49 → 0.17 | 0.3 → 0.0 | 0.34 → -1.06 | 2.32 → 2.43 |
| `fiat/price/5pt` | 5.1 → 4.8 | 2.6 → 1.7 | 24 → 18 | 9.0 → 9.0 | 11.0 → 11.0 | 0.8 → 0.9 | 0.34 → 0.20 | 0.2 → 0.0 | -0.21 → -1.14 | 2.25 → 2.29 |
| `fiat/growth/0pt` | 17.0 → 16.0 | 11.7 → 9.9 | 23 → 21 | 10.0 → 10.0 | 12.7 → 12.0 | 2.2 → 2.1 | 0.01 → 0.02 | 0.0 → 0.0 | -0.68 → -1.14 | 3.25 → 3.22 |
| `digital/price/0pt` | 9.0 → 8.3 | 6.1 → 4.8 | 23 → 23 | 10.0 → 10.0 | 11.0 → 11.0 | 1.2 → 1.2 | 0.24 → 0.17 | 0.3 → 0.0 | -0.66 → -1.03 | 2.38 → 2.39 |

**`--wage-pressure 1.0`** — labour laws worth +1pp:

| cell | crashes | recession % | longest <40, mo | peak rate | p90 peak | rate ≥10 % | tight in slump % | policy downturns | post-crash stance | inflation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `gold/price/0pt` | 5.5 → 5.3 | 6.2 → 3.8 | 46 → 41 | 9.7 → 9.7 | 11.0 → 11.0 | 0.2 → 0.2 | 1.62 → 0.41 | 1.6 → 0.2 | 0.14 → -0.68 | 0.58 → 0.59 |
| `fiat/price/0pt` | 0.9 → 0.8 | 4.0 → 1.3 | 91 → 106 | 12.0 → 12.0 | 14.0 → 14.0 | 10.6 → 11.1 | 3.83 → 3.13 | 4.2 → 0.6 | 1.00 → -0.37 | 3.60 → 3.67 |
| `fiat/price/5pt` | 0.1 → 0.1 | 2.2 → 0.4 | 75 → 76 | 12.0 → 12.0 | 14.0 → 14.0 | 10.4 → 10.6 | 4.57 → 3.44 | 2.8 → 0.4 | 0.97 → 0.12 | 3.62 → 3.64 |
| `fiat/growth/0pt` | 5.0 → 3.4 | 24.4 → 6.1 | 295 → 71 | 21.0 → 14.0 | 25.0 → 18.0 | 53.4 → 29.4 | 21.45 → 4.36 | 8.3 → 1.9 | -0.38 → -0.48 | 8.66 → 5.32 |
| `fiat/growth/5pt` | 3.7 → 1.9 | 17.0 → 3.1 | 202 → 50 | 21.0 → 13.0 | 25.0 → 18.0 | 49.9 → 26.7 | 20.30 → 3.95 | 7.5 → 1.5 | -0.63 → -0.61 | 8.48 → 5.19 |
| `digital/growth/0pt` | 5.0 → 3.1 | 18.8 → 5.4 | 177 → 62 | 22.0 → 13.0 | 25.0 → 19.0 | 52.8 → 30.0 | 20.98 → 5.21 | 8.4 → 2.1 | -0.68 → -0.35 | 8.79 → 5.31 |

At +0.5pp the direction is the same and smaller. Fiat price stability's recession share goes 3.3 → 1.6% and its
policy downturns 1.1 → 0.1. Fiat growth's p90 peak goes 18 → 14 and its months at 10% or more 16 → 9.

**The calm-world trade growth was tuned for survives.** With no wage pressure, fiat growth against price
stability is 3.2% against 2.4% inflation, +0.17 against −0.11pp of manufacturing throughput, and +4.3%
against +2.7% services. At 0 points, throughput and services rise in every price and growth cell at 0, +0.5 and
+1pp.

**Sensitivities** (200 runs, +0.5pp): `--pulse-order monetary_first`, where the outlook reads a month-stale
momentum, and `--event-channel` both move in the same direction by about the same amount. **Boom rescue**
(`--rescue`): the passive arm stays at 0.2–3.9% (0.2–5.7% before). The maxed arm goes 25–53% → 34–50%;
digital is within noise.

### F15 — Not fixed: the standing-pressure trap (owner decision)

The package changes *how* a bank moves, not *where* the balance of pressures puts it. Against +1pp of
wage pressure, price stability needs a standing stance near +2.5 (−0.4pp of pressure per point, and the +4
clamp buys at most −1.6pp). So fiat price stability still peaks at 12% (p90 14%) and spends about 11% of its
months at 10% or more. The economy sits near the stagnation line: mean cycle about 40, and the longest run
below 40 is 91 → 106 months — shallower, since recession months fall 4.0 → 1.3%, but longer.

With +1pp *and* a 3% average deficit (`--deficit-mean 3`) the fiat bank is overwhelmed. Recession months go
20 → 17% and policy downturns 11.0 → 4.6, but the rate is at 10% or more 40–45% of the time with a p90 peak
at the 25% ceiling, and growth still averages 8.7% inflation (14.5% before).

No reaction function tried above removes this without letting inflation escape. The levers are outside the
bank: the size of the wage-pressure grants, `te_mon_stance_pressure_coeff` (0.4), or a real-balance pull
under fiat (§4's `fiat_pull`). **§13 takes the first route for independent banks:** inflation anchoring
absorbs up to 0.1pp of standing pressure per National Bank level.

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --years 100 --points 0,2,5,8                                  # shipped
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --years 100 --points 0,2,5,8 --tune pre_delegation_fix        # before
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --years 100 --points 0,2,5 --wage-pressure 1.0 [--tune pre_delegation_fix]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --years 100 --points 0,5 --wage-pressure 1.0 --deficit-mean 3 [--tune pre_delegation_fix]
```

---

## 13. Central bank independence: inflation anchoring instead of crash and momentum damping (2026-09-25)

**Question (owner).** §12's F15 left price stability peaking at 12–14% under +1pp of standing wage
pressure, with the cycle held near stagnation. Separately, independence's per-level bonus on top of the
National Bank institution's own modifier — −5% `country_banking_crash_chance_mult` and −2%
`country_banking_random_momentum_mult` a level — looked weak and partly self-defeating. A lower crash
chance means crashes come later and off bigger bubbles. Damper random momentum means a frenzy is less
likely to be broken by chance. Could that bonus reduce inflation pressure instead?

The simulator now ports the institution: `--bank-level N` scales `institution_national_bank`'s modifier
and the financial law's `institution_modifier`. Every other financial-law line is still unported (§10).

### F16 — The old bonus bought a little boom time and slightly worse crashes

Independence, 400 runs, +0.5pp wage pressure, level 9 (−45% crash chance, −18% random momentum), each line
alone and together:

- **Crash chance alone:** crash counts barely move (fiat 1.89 → 1.85 a century, gold 4.43 → 4.33). Crashes
  come off bigger bubbles (gold 85 → 90 at the crash), severity rises, gold's depression share rises
  26 → 28%, and gold spends twice as long in frenzy. It also buys boom time: services output rises.
- **Random momentum alone:** crashes are mixed (fiat −8%, gold at 8 points +9%) and services fall. The
  random nudge is weighted back toward 50, so damping it also slows recoveries.
- **Frenzy escapes** are too rare under a delegated independent bank to measure: frenzy occupies 0.02–0.7%
  of months.

With no wage pressure the pair was worth about −10% crashes and +1pp of services at level 9. That is small,
and it is what dropping it costs (table below, `+0pp` rows).

### F17 — A flat pressure reduction makes the bank run loose; a capped one does not

Two forms of a per-level reduction were measured, with a scratch harness at 250 runs and 0 points:

| form | no wage pressure | under wage pressure |
|---|---|---|
| **flat** `country_inflation_pressure_add` −0.05 / −0.1pp a level | Crashes **double to triple** (independent fiat at level 9: 8.7 → 17.5 at −0.05, → 23.9 at −0.1) and inflation undershoots to 1.4–1.9%. With nothing to offset, the bank holds a permanently loose stance to reach its target. | Same as capped while the reduction is smaller than the pressure. |
| **capped** — absorbs up to the capacity of the net positive wage + price pressure, never past zero | **Exactly no effect** (identical runs). | Same as flat until the pressure is fully absorbed, then stops. |

The capped form is what shipped. The same measurement on a non-independent delegated bank (universal
banking) gave the same shape, so the grant would work on the base institution too (below).

### What shipped

`law_central_bank_independence`'s `institution_modifier` is now `country_inflation_anchoring_add = 0.001`
(+0.1pp a National Bank level, 0.9pp at nine). `te_mon_pressure_anchoring` = clamp(wage + other modifier
pressure, 0, capacity) is subtracted in `te_mon_pressure_modifiers`. The dashboard shows an **Inflation
Anchoring** row ("absorbed / capacity") under the two pressure rows, for a country that holds any. 0.1pp a
level also renders cleanly: the modifier type shows one decimal, so 0.05pp would print as 0.0% or 0.1%.

### Result — independent bank, 200 runs × 100 years, `--tune pre_anchoring` → shipped, 0 points unless marked

| CBI cell (level, wage) | crashes | recession % | longest <40 | peak | p90 peak | rate ≥10 % | inflation | cycle | throughput | services |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `digital/price` L9, +1pp | 0.4 → 6.4 | 0.4 → 3.9 | 55 → 20 | 11.0 → 10.0 | 13.0 → 11.0 | 4.6 → 0.8 | 3.23 → 2.39 | 42.0 → 50.1 | -1.95 → 0.22 | -3.49 → 3.40 |
| `fiat/growth` L9, +1pp | 9.4 → 17.4 | 8.0 → 11.0 | 27 → 20 | 12.0 → 10.0 | 15.1 → 12.0 | 9.4 → 1.0 | 4.40 → 2.94 | 50.2 → 52.0 | 0.21 → 0.47 | 3.78 → 5.56 |
| `fiat/price` L9, +0pp | 8.2 → 9.0 | 6.0 → 6.1 | 21 → 21 | 10.0 → 10.0 | 11.4 → 11.0 | 1.0 → 0.9 | 2.33 → 2.31 | 51.6 → 50.5 | 0.67 → 0.29 | 5.17 → 3.97 |
| `fiat/price` L9, +0.5pp | 1.7 → 8.9 | 1.3 → 5.9 | 32 → 20 | 10.0 → 10.0 | 12.0 → 11.0 | 1.5 → 0.5 | 2.76 → 2.32 | 44.3 → 50.5 | -0.91 → 0.29 | -0.93 → 3.95 |
| `fiat/price` L5, +1pp | 0.8 → 1.9 | 0.8 → 1.4 | 58 → 32 | 11.0 → 10.0 | 13.0 → 12.0 | 4.2 → 1.5 | 3.24 → 2.76 | 41.5 → 44.7 | -2.09 → -0.91 | -3.65 → -0.90 |
| `fiat/price` L9, +1pp | 0.8 → 7.2 | 0.8 → 4.9 | 55 → 22 | 11.0 → 10.0 | 13.0 → 11.0 | 4.0 → 0.9 | 3.23 → 2.42 | 41.4 → 49.2 | -2.11 → 0.04 | -3.68 → 2.83 |
| `fiat/price` L9, +0.5pp, 8pt | 0.5 → 3.5 | 0.1 → 0.5 | 19 → 16 | 10.0 → 9.0 | 12.0 → 10.7 | 1.4 → 0.4 | 2.75 → 2.34 | 45.2 → 52.2 | -0.47 → 0.97 | 0.12 → 5.59 |
| `gold/price` L9, +0pp | 6.3 → 6.7 | 6.2 → 5.4 | 39 → 35 | 10.0 → 10.0 | 11.3 → 11.0 | 0.4 → 0.2 | 0.13 → 0.13 | 48.7 → 47.9 | -0.23 → -0.48 | 2.42 → 1.43 |
| `gold/price` L9, +1pp | 2.5 → 6.4 | 2.2 → 5.2 | 34 → 36 | 9.8 → 10.0 | 11.0 → 11.0 | 0.3 → 0.2 | 0.61 → 0.18 | 45.1 → 47.7 | -0.89 → -0.51 | -0.56 → 1.35 |

**Under standing pressure the bank is let out of stagnation.** At +1pp and level 9, fiat price stability's
p90 peak goes 13 → 11%, months at 10% or more 4.0 → 0.9%, and the longest run below 40 goes 55 → 22 months.
The mean cycle goes 41 → 49, throughput −2.1 → 0.0pp and services −3.7 → +2.8%. **Crashes rise with
it**, 0.8 → 7.2 a century, and recession months 0.8 → 4.9%. That is the calm-world rate: the low count
before was the stagnation itself, a bank too tight for a boom to form. Growth tells the same story (fiat
+1pp: crashes 9.4 → 17.4, inflation 4.4 → 2.9%, p90 peak 15 → 12%). Gold changes least, since its regime
pull already absorbs most standing pressure. Level 5 lands about halfway.

**With no standing pressure, independence is a little worse than before**, by exactly what the old bonus
was worth (F16). Recession months and peak rates are unchanged.

### Owner decisions

- **Placement.** Only independence carries the grant, so a delegated bank without independence still sits
  in §12's F15 trap. Putting the same line on `institution_national_bank`'s own modifier would reach every
  National Bank country. Measured on a universal-banking delegated bank at level 9 and +1pp: p90 peak
  14 → 12%, longest slump 104 → 30 months, mean cycle 40 → 47, services −5.5 → +1.4%, crashes 0.8 → 6.5.
  Independence would then want something else that sets it apart, or a larger capacity.
- **Size.** 0.1pp a level fully absorbs +0.5pp of wage pressure from level 5, but at most 0.9 of +1pp (at level 9).

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 0 --fin-law law_central_bank_independence --bank-level 9 --wage-pressure 1.0 [--tune pre_anchoring]
```

---

## 14. Five directed-credit sectors, five profiles (2026-09-30)

**Question (owner).** The five sectors of §11 read as one tool with five labels: 3 points, 0.8% of GDP, +10%
construction for a building group, an interest-group line, and momentum and bubble within 0.01 and 0.2 of each
other. Make them distinct, and price each differently (Electrification cheap).

**What shipped.** Each sector has its own price, cycle signature and a second effect beyond construction
(`extra_modifiers.txt`, the table above `banking_directed_credit_infrastructure`):

| Sector | Points | Momentum / bubble per month | Second effect | Liability |
|---|---|---|---|---|
| Infrastructure | 3 (was 3) | 0.03 / 0.1 (was 0.05 / 0.3) | infrastructure +5% in every state | Industrialists −3 (was −5) |
| Heavy Industry | 4 (was 3) | 0.06 / 0.5 (was 0.05 / 0.3) | heavy-industry throughput +5% | greenhouse gas emissions +5%; Industrialists +2 (was +3) |
| Agriculture | 2 (was 3) | 0.03 / 0.4 (was 0.04 / 0.4) | food security +5% | the worst momentum for its bubble |
| Armaments | 3 (was 3) | 0.06 / 0.05 (was 0.05 / 0.2) | military throughput +5%, military goods cost −10% | Intelligentsia −3 (was −2) |
| Electrification | 1 (was 3) | 0.04 / 0.2 (was 0.05 / 0.3) | electricity output +5% | covers power plants only; era-gated |

The simulator reads points and both monthly lines from those modifiers, so it needed no change for them. It cannot
see what construction, throughput, food security, emissions or interest-group approval are worth, so those lines
are sized by judgement, and what the simulation checks is the cycle signature and the AI.

### F18 — The Directed Credit law's second slot did not fit its own budget

`law_directed_credit_development_banks` grants a budget of 5 (6 with a national bank) and a second sector, but
two 3-point sectors cost 6. Below the national bank the second slot could not be filled, and with it the two
sectors took every point and left nothing for a lean or a crisis tool. At 1 / 2 / 3 / 4 points Electrification
fits beside any sector and Agriculture beside Infrastructure or Armaments; the sixth point adds Infrastructure
with Armaments and Heavy Industry with Agriculture, and Heavy Industry never sits beside Infrastructure or
Armaments.

### F19 — Cheap sectors at real prices: the AI uses them far more, and holds them too long

The AI pays the same points as a player. Its button and the dashboard's run the same `banking_effect_cb_*`, which
adds the sector's modifier and its `country_banking_intervention_max_add`, so every later `possible` check and
points-based weight reads the reduced budget. A sector priced at 1 or 2 is therefore affordable at budgets, and in
half-spent budgets, where a 3-point sector was not. An earlier draft held the AI's click count constant by making
every sector a candidate only above three free points. That changed when the AI pressed the button and nothing about
what it cost, so the AI's other decisions saw the full reduction either way. It was dropped in favour of adjusting the
AI's weights.

At real prices with the AI's lift weights unchanged, directed-credit clicks a century roughly doubled, almost all of
it in Electrification (1 point) and Agriculture (2): with all four favoured they went from 26.7 / 25.5 to 137 / 72, and
at a 2-point budget the AI, which never directed credit there, made 13–14 clicks. Crashes rose with them, most in the
growth mandate at 3 points (13.1 → 14.3 at 600 runs). The harm is F11's, holding directed credit through the
recovery, so the fix is the lift side, which is an AI preference and not a price: every sector's disable button now
adds 40 in Stable (momentum not falling) and 50 in Expansion, where it added 20 and 30. `--tune dc_lift_boost=0`
restores the old weights.

### Result — 150 runs × 100 years per cell, fiat, 2 / 3 / 4 / 5 / 8 points (4 / 5 / 6 / 8 under the law), before → real prices, old lift → shipped

Directed-credit clicks a century, summed over the grid, and mean crashes a century over the price-stability and
growth cells (the no-touch cells are flat):

| affinity | clicks | crashes |
|---|---|---|
| none | 103.9 → 105.0 → 108.3 | 8.85 → 8.82 → 8.93 |
| heavy industry | 104.5 → 105.2 → 108.9 | 8.28 → 8.42 → 8.43 |
| electrification | 104.5 → 200.2 → 209.6 | 8.28 → 8.86 → 8.55 |
| all four | 105.2 → 247.0 → 258.4 | 8.97 → 9.24 → 8.92 |
| all four, Directed Credit law | 149.6 → 334.7 → 344.0 | 9.02 → 9.32 → 9.00 |

With all four favoured, shipped, Heavy Industry drops from 26.7 to 12.8 clicks (it costs 4, so it is out of reach at
3 points) while Agriculture and Electrification rise to 76 and 143; Armaments is unchanged (27). Infrastructure, the
default sector, is clicked as often as before (94.9 → 95.7 with no affinity, before the lift change) at lower
momentum and bubble.

**What remains.** The AI directs credit about twice as often wherever a cheap sector is favoured, by design of the
prices, and crashes are back to the old level in the all-four cells. Two cells stay slightly above it: favouring
electrification alone (8.28 → 8.55) and fiat / growth at 3 points with all four favoured, 600 runs (13.1 → 13.5; price
stability 6.3 → 6.5). Raising the lift weights further (stable 55, expansion 65) moved the all-four cells by under
0.1, so the rest is the cost of the extra months spent in directed credit. The 2-point cells with no sector favoured
are unchanged, and §8's targets do not depend on any of this.

**Further levers, not tried.** A lower enable weight (`banking_dc_ai_weight`), for every sector or only the cheap ones.

**Not re-run.** The leave-one-out of each new sector, the currency laws other than fiat, and the 400-run matrix.

**Reproduce** (`before` is the commit before this change; the middle column is `--tune dc_lift_boost=0`):

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 150 --only fiat --points 2,3,4,5,8 [--dc-affinity dc_heavy,dc_agri,dc_arms,dc_elec] [--tune dc_lift_boost=0]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 150 --only fiat --points 4,5,6,8 --fin-law law_directed_credit_development_banks --dc-affinity dc_heavy,dc_agri,dc_arms,dc_elec
```

---

## 15. The mandate bank's asset purchases at the rate floor (2026-10-01)

**Question (owner).** A player on Central Bank Independence and Digital Currency was stuck in deflation with the
policy rate on the −3% floor and headline inflation at −6.6%. Central Bank Independence rules out Monetise Deficit, and
at the floor both mandates ask for less than the floor allows. What can a mandate-run bank do?

### F20 — At the floor the bank has no lever of its own, and without Open-Market Operations the loop has no exit

The model is §9.1's: core moves a tenth of the way to `expected + pressure` each month, and expectations lose their
anchor once inflation is ten points from target (`c_eff`). At −6.6% an independent bank has `c_eff` of about 0.1, so
expectations follow headline, and the only upward pressure is Open-Market Operations' flat +1.0, which costs 4 intervention
points. Started as reported (core −4.2 under a −2.4 cost-push drag that fades as its average catches up, expected −4.9, rate
−3, 0.9 of wage pressure absorbed by nine National Bank levels, cycle held at 50, no noise), headline reaches 0 after
five years with Open-Market Operations on. With it off, headline falls to the −10 clamp and stays there.

### What shipped first

`te_mon_pressure_bank_qe`, `min(2.5, 0.5 × (anchor − last month's headline))` pp, while a mandate-run fiat or digital
bank sat on its rate floor. Measured with the inflation noise held at zero, it got out of the trap, and switched off once
when the bank's rate left the floor.

### F21 — With the noise on, the first version flickered at the floor

The term was gated on the real rate being on the floor, so the month the rate rose by one drift step (−3.00 → −2.33 under
digital) it dropped from 2.5 to 0. Inflation stalled, the mandate's target fell back, the rate returned to the floor and
the term came back. Over 200 seeds, a delegated digital bank switched 3.41 times a run on average (at most 7), every 2–6
months for about two years, and a month's change in the term reached 2.5.

### What shipped instead: a virtual rate

The bank keeps a virtual target and rate (`te_mon_virtual_target` / `te_mon_virtual_rate`, design doc §0.12) where it would
put them without the floor: the mandate formula with the real target's hysteresis, drifting at the real rate's speeds, at
most 5 points under the floor (2.5 until F22 below). The real rate is the virtual one held at the floor, and the
purchases are `min(5, 1.0 × (floor − virtual rate))`. Price stability may take the virtual target under the floor only while headline
is under the anchor; growth always may. The simulator ports it as `settle_virtual_rate`, `update_virtual_target`,
`monetary_drift_rate` and `bank_qe_pressure`; `--tune pre_bank_qe` keeps the virtual target on the floor, which is the
pre-§0.12 world exactly.

### Result

`scripts/analysis/banking_deflation_trap.py` starts the reported country (core −4.2 under a −2.4 cost-push drag that fades
as its average catches up, expected −4.9, rate −3, 0.9 of wage pressure absorbed by nine National Bank levels, cycle held at
50). "First version" is the same script on that version's commit; "virtual rate" is the shipped cap of 5, which this trap
barely reaches (its purchases peak at 4 without Open-Market Operations and 3 with them).

| Headline inflation at year, noise held at zero | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| independent, Open-Market Operations on, before | −6.0 | −5.0 | −3.4 | −1.7 | +0.1 | +1.2 |
| independent, Open-Market Operations on, first version | −3.3 | −2.3 | −0.8 | +0.5 | +1.4 | +1.9 |
| independent, Open-Market Operations on, virtual rate | −4.1 | −2.7 | −1.1 | +0.3 | +1.3 | +1.8 |
| independent, no Open-Market Operations, before | −7.1 | −7.6 | −8.3 | −9.3 | −10 | −10 |
| independent, no Open-Market Operations, first version | −4.3 | −3.1 | −2.2 | −1.0 | 0.0 | +0.7 |
| independent, no Open-Market Operations, virtual rate | −4.5 | −3.3 | −2.5 | −1.3 | −0.2 | +0.6 |
| manual dial, Open-Market Operations on, every version | −5.1 | −3.8 | −2.7 | −1.5 | −0.4 | +0.7 |

| Noise on, no Open-Market Operations, 200 seeds | Switches on/off, mean (max): first version → virtual | Largest one-month change | Median month at 0% |
|---|---|---|---|
| independent, digital, price stability | 1.82 (5) → 1.05 (3) | 2.50 → 0.67 | 60 → 63 |
| delegated, digital, price stability | 3.41 (7) → 1.38 (5) | 2.50 → 0.67 | 71 → 75 |
| delegated, fiat, price stability | 2.18 (5) → 1.07 (3) | 1.87 → 0.33 | 66 → 68 |
| delegated, fiat, growth | 2.18 (5) → 1.07 (3) | 1.87 → 0.33 | 66 → 68 |

The virtual rate gives up two to four months of the exit and moves the purchases by at most a drift step a month (×3 in
a Stagnation's emergency cuts, on the way in only). The real rate leaves the floor only once they are at zero.

Ordinary play does not move. With and without independence, 150 fiat runs per cell differ from `--tune pre_bank_qe` by
at most 0.03 crashes a century, 0.006 points of mean inflation and 0.04 points of recession share, and 60 digital runs per
cell are identical in every column: a mandate bank is on its floor in at most 0.2% of months under fiat and never under
digital. Over 40 ordinary centuries per cell, a mandate bank buys in at most 0.05% of months under fiat, about 0.6 points on average while it does, and never under digital. A Growth bank buys with headline at or above target in 0.01% of months, the only place the mandate condition binds.

A delegated bank without independence can monetise beside its own purchases (design doc ruling N1, resolved as intended
pending playtests). Stacking adds almost nothing: Monetise Deficit's inflation (added by the trap script, since the
simulator does not model monetisation) lifts the bank's rule off the floor within months.

| Price Stability, noise held at zero | Month at 0%: without / with purchases | Peak inflation: without / with | Months buying |
|---|---|---|---|
| Monetise Deficit off | 98 / 76 | 1.3 / 1.9 | 19 |
| Monetise Deficit 1 | 37 / 35 | 5.4 / 5.4 | 8 |
| Monetise Deficit 3 | 11 / 11 | 25.6 / 25.8 | 4 |

**Not modelled in the tables above.** The exchange-rate channel, and the cycle: the Deflation band's momentum drain and
the Stagnation phase term would make a real recovery slower. F22 shows how much slower.

### F22 — A Panic and a strong currency held the first cap on the −10% clamp (playtest, 2026-10-01)

A playtest put an independent Digital country on Growth in Panic, with the policy rate on −3, headline on the −10% clamp for
ten months, expected −9.1, a currency at 125.3 importing −2.6 points, and the bank's purchases at their cap of 2.5 beside
Open-Market Operations. Those +3.5 points matched the Panic (−1.5) and the Very Tight stance (−1.6); the currency took the
rest from headline, and expectations twelve points off target followed it down. The deflation lifts the currency (both its
real-rate and inflation-gap terms) and the tight stance holds the Panic, so the state feeds itself.

`banking_deflation_trap.py --playtest-only` starts from that screenshot (core, hidden under the pinned headline, assumed
−8.5), runs the cycle, and adds the script's currency loop (`CurrencyLoop`, after `te_monetary_fx_script_values.txt`, with
the cyclical premium held at 4.5 and the basket neutral; the simulator itself still imports nothing, through its new
`fx_imported` hook). Medians of 60 seeds:

| Playtest start | Leaves −10% (month) | Reaches 0% (month) | Peak in the 3 years after | Mean, years 8–10 |
|---|---|---|---|---|
| Growth, before (cap 2.5, two-sided confidence) | 38 | 90 (48 of 60) | 5.7 | 1.7 |
| Growth, cap 5 alone | 5 | 40 | 5.3 | 5.2 |
| Growth, one-sided confidence alone (cap 2.5) | 5 | 41 (59 of 60) | 3.9 | 3.8 |
| Growth, shipped (cap 5, one-sided) | 3 | 27 | 4.0 | 3.9 |
| Price Stability, before | 38 | 90 (48 of 60) | 5.4 | 1.7 |
| Price Stability, shipped | 3 | 27 | 3.7 | 2.8 |
| Growth, before, Restrict Speculative Inflows in place of Bail-in | 16 | 79 (51 of 60) | 5.3 | 3.8 |
| Growth, before, no currency loop | 1 | 49 | 3.0 | 3.3 |

Two changes shipped (design doc §0.12, "The cap and the currency"). The cap went to 5: the century matrix reruns at 5 to
the same figures as at 2.5 (150 fiat runs per cell, 60 digital, with and without independence). And the exchange rate's
confidence term is one-sided for a float (ruling N10): half the playtest's currency rise was that term rewarding the
deflation, on top of the carry term that already pays for holding a currency that gains value, and the rise then came
back as imported deflation. Together they get the playtest off the clamp in about three months and to 0% in about 27,
and the rebound settles lower because the currency no longer overshoots and falls back. Outside the trap, ordinary centuries of floating countries with the same currency loop on (`banking_deflation_trap.py --ordinary-runs 30`; the century simulator itself holds the exchange rate at par) spend about half as many months below 0% (a delegated digital bank 1.24% of months → 0.22%), mean inflation moves by at most 0.2 points, and crash rates are unchanged within noise: the two Growth cells, rerun at 100 centuries, differ by −0.2 ± 0.7 and +0.4 ± 0.7 crashes a century.

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_deflation_trap.py [--runs 200] [--playtest-runs 60] [--playtest-only] [--ordinary-runs 30]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 150 --only fiat --points 0,8 --seed 1 [--fin-law law_central_bank_independence] [--tune pre_bank_qe]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 60 --only digital --points 0,8 --seed 1 [--fin-law law_central_bank_independence] [--tune pre_bank_qe]
.venv/bin/python -m unittest test_monetary_bank_qe
```

---

## 16. A slump's pull on prices under an inflation target (2026-10-02)

**Report (owner).** A fiat central bank kept raising its rate through a Panic to hold inflation down. A
slump should be disinflationary enough that the bank can follow it down. The cycle's phase term in
`te_mon_phase_pressure` (§9.1 of the design doc) was −0.3 / −0.8 / −1.5 for Stagnation, Downturn and Panic,
the mirror of the boom side, under every currency.

The simulator now reads that value from the mod rather than restating it (`ModConstants.phase_table`), takes
`--tune pressure_<phase>=X` (inflation-target side) and `pressure_metal_<phase>=X`, and has two new columns:
**rcHike**, the share of Panic and Downturn months in which the policy rate rose, and **rcCore**, core
inflation's mean change over those months in pp a year. `--tune pre_slump_pressure` restores the old slump
side.

### F23 — The slump terms could not move a fiat bank's inflation

Fiat, price stability, no wage pressure: core inflation fell about 0.5pp a year through a recession, and the
policy rate rose in 27% of recession months. Under +1pp of wage pressure, core sat near 4.7% through slumps
and the target near 8%. A labour law's wage pressure (+0.2 to +1.4pp across the labor and welfare laws)
outweighed a Downturn's −0.8 on its own. The phase term is a level, and core closes a tenth of the gap a
month, so −1.5 through a typical year-long Panic moves core about a point.

### F24 — Metal cannot take a larger pull

Three candidates applied to every currency, 200 runs × 100 years, no wage pressure (old → A → B → C, where A
is −0.5 / −1.5 / −3, B −0.75 / −2 / −4 and C −1 / −3 / −5):

| cell | crashes | recession % | longest <40, mo | Deflation band % | services % |
|---|---:|---:|---:|---:|---:|
| `commodity/nothing/0pt` | 8.2 / 7.6 / 6.4 / 4.2 | 11.7 / 24.2 / 38.3 / 62.7 | 75 / 176 / 277 / 558 | 6.8 / 20.9 / 36.9 / 63.2 | −1.5 / −7.5 / −15.0 / −28.2 |
| `gold/peg/0pt` | 12.9 / 11.9 / 9.9 / 6.4 | 11.2 / 17.2 / 30.4 / 56.6 | 41 / 82 / 188 / 456 | 3.1 / 11.3 / 26.8 / 55.6 | 2.0 / −1.4 / −8.8 / −23.7 |
| `commodity/price/0pt` | 9.5 / 9.1 / 8.9 / 7.7 | 6.9 / 8.1 / 10.5 / 15.8 | 33 / 46 / 58 / 96 | 2.4 / 5.0 / 9.1 / 17.9 | 2.5 / 1.7 / 0.6 / −2.8 |
| `fiat/price/0pt` | 8.8 / 10.3 / 12.1 / 13.6 | 5.7 / 6.4 / 7.9 / 8.7 | 26 / 23 / 21 / 22 | 0.0 / 0.0 / 0.1 / 0.4 | 2.8 / 3.6 / 4.1 / 4.3 |
| `fiat/growth/0pt` | 16.0 / 17.9 / 19.2 / 20.4 | 9.9 / 10.5 / 11.2 / 11.9 | 21 / 20 / 20 / 20 | 0.0 / 0.0 / 0.0 / 0.1 | 4.2 / 4.9 / 5.1 / 5.2 |

Metallic prices rest at 0%, a point above the Deflation band's −1% edge, and the regime pull settles core at
half the pressure. A larger slump pull puts a metallic economy into Deflation, whose −0.2 monthly momentum
drain then holds the slump: a self-sustaining depression. Fiat and digital prices rest near the 2% anchor,
three points from the edge, and a mandate bank's cell barely enters the band at C.

### What shipped

`te_mon_phase_pressure`'s slump side splits on a new trigger, `te_mon_targets_inflation`: inflation anchor
above 0 (fiat, digital, a suspended gold standard, or a currency anchored to one of those), not dollarised,
not decentralized cryptocurrency. There it is **−0.5 / −2 / −4**: B with the milder Stagnation the owner asked
for. Metal, dollarised and crypto money keep −0.3 / −0.8 / −1.5. The boom side is unchanged everywhere.

### Result — 400 runs × 100 years per cell, `pre_slump_pressure` → shipped

Every metallic cell is identical run for run. Fiat and digital mandate cells:

| cell | crashes | recession % | longest <40, mo | inflation | rate ≥10 % | tight in slump % | rcHike | rcCore | services % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fiat/price/0pt` | 8.5 → 11.3 | 5.5 → 7.3 | 26 → 23 | 2.43 → 2.22 | 1.2 → 0.9 | 0.17 → 0.14 | 27.1 → 14.2 | −0.47 → −1.49 | 2.7 → 3.6 |
| `fiat/price/5pt` | 5.0 → 5.6 | 2.1 → 2.4 | 19 → 19 | 2.37 → 2.28 | 1.1 → 0.8 | 0.21 → 0.15 | 27.3 → 15.2 | −0.37 → −1.45 | 4.8 → 5.4 |
| `fiat/growth/0pt` | 16.1 → 18.8 | 9.9 → 10.9 | 21 → 20 | 3.22 → 2.82 | 2.1 → 1.2 | 0.02 → 0.01 | 20.8 → 16.4 | −0.83 → −1.94 | 4.3 → 5.0 |
| `digital/price/0pt` | 8.3 → 10.5 | 4.8 → 5.9 | 23 → 21 | 2.39 → 2.20 | 1.2 → 1.0 | 0.17 → 0.11 | 32.7 → 25.9 | −0.40 → −1.60 | 3.7 → 4.6 |
| `digital/growth/0pt` | 15.1 → 17.3 | 8.6 → 9.5 | 21 → 20 | 3.15 → 2.80 | 2.1 → 1.5 | 0.03 → 0.02 | 19.8 → 18.5 | −0.82 → −1.98 | 5.0 → 5.5 |

**`--wage-pressure 1.0`**, where §12's F15 left price stability parked near the stagnation line:

| cell | crashes | recession % | longest <40, mo | inflation | rate ≥10 % | tight in slump % | rcHike | rcCore | services % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fiat/price/0pt` | 0.8 → 1.0 | 1.3 → 0.9 | 106 → 84 | 3.67 → 3.49 | 11.1 → 8.1 | 3.13 → 1.91 | 20.1 → 19.1 | −0.37 → −1.32 | −5.5 → −4.6 |
| `fiat/price/5pt` | 0.1 → 0.1 | 0.5 → 0.2 | 80 → 62 | 3.67 → 3.48 | 11.2 → 7.6 | 3.64 → 2.18 | 11.2 → 9.7 | −0.57 → −1.42 | −5.1 → −4.4 |
| `fiat/growth/0pt` | 3.4 → 4.7 | 6.1 → 4.3 | 71 → 52 | 5.32 → 5.01 | 29.4 → 23.1 | 4.36 → 1.51 | 12.3 → 11.8 | −0.43 → −1.57 | −2.9 → −1.2 |
| `digital/price/0pt` | 0.4 → 0.5 | 1.0 → 0.5 | 83 → 70 | 3.68 → 3.51 | 11.9 → 9.0 | 3.56 → 2.15 | 17.7 → 20.1 | −0.38 → −1.30 | −5.0 → −4.3 |
| `digital/growth/0pt` | 3.1 → 4.2 | 5.4 → 3.8 | 62 → 50 | 5.31 → 5.03 | 30.0 → 25.1 | 5.21 → 2.06 | 10.6 → 10.5 | −0.40 → −1.54 | −2.4 → −0.8 |

At +0.5pp (300 runs) the direction is the same: fiat price stability's longest slump 52 → 43, rcHike
28.6 → 19.2, crashes 2.3 → 3.3, services −2.0 → −1.0.

**Core now falls through a recession**, two to four times as fast, and inflation averages closer to the 2%
target. Under standing wage pressure the bank spends less time at 10% or more and less time tight in a slump,
and the longest slump shortens by about a fifth. **Crashes rise** with no wage pressure (fiat price stability
8.5 → 11.3 a century at 0 points, 5.0 → 5.6 at 5): the bank comes out of each slump looser. Services output
rises in every fiat and digital mandate cell. The unsteered fiat and digital dials (`*/nothing`, F5) drift
less (fiat 18.4% → 9.9% mean inflation) and now sit tight in a slump 3% of the time, the cost of holding a
fixed rate while prices fall.

### F25 — Not fixed: the remaining hikes are the outlook, not inflation

Hikes in Panic nearly vanish (no wage pressure, fiat price stability, 60 runs: 98 Panic months with a hike
before, 6 now). About 96% of the 708 hike months left falls in a Downturn 6–18 months after a crash, with the outlook already past 25: the lean
(§12) switches off while the phase line has not yet been crossed, and the target returns to its rule. Core
then sits below target (about 1.5%), so this is a stimulative rate going back to neutral, not a bank fighting
inflation. Holding the slump lean until the phase itself leaves Downturn would remove it, at the cost of §12's
"stop leaning before the line" behaviour, which is an owner decision.

### Deflation trap

`banking_deflation_trap.py`'s playtest start (§15, F22: Panic, headline on −10%, a strong currency), 60 seeds:
the bank leaves the clamp in month 4 (3 before) and reaches 0% in month 32 (27), with the same peak (4.0 Growth,
3.8 Price Stability) and a late mean 0.2 lower. Ordinary centuries with the currency loop on, 30 per cell: no months on the
−10% clamp, months below 0% at most 0.64% (at most 0.41% before), crashes unchanged within noise.

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --points 0,5 [--wage-pressure 1.0] [--tune pre_slump_pressure]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 0,5 --tune pressure_metal_stagnation=-0.75,pressure_metal_downturn=-2,pressure_metal_panic=-4   # F24's B on metal
```

---

## 17. Crash ceilings (2026-10-05)

The crash tiers (value 5…40, momentum −5…−1) were absolute resets, so a crash could lift a country that was already below the tier, and a softening response could add on top of that. The script now treats the tier figures as ceilings and holds every option to the pre-crash level (`docs/systems/mod_systems.md`, Monthly Pulse step 3; `test_banking_crash_no_raise.py`). `apply_crash` ports both.

The simulator only models the origin crash, which fires from a high cycle, so it barely sees the bug. Wrapping `apply_crash` to compare each crash's figures before and after (100 runs × 100 years in each of the 26 cells at 0 and 5 points, a one-off, not kept in the repo): before, 17,211 crashes, 0 of which raised cycle value and 3 of which raised momentum (by up to 0.31); after, 17,215 crashes and 0. Trajectories diverge after the first changed crash, so the cells are not comparable beyond noise: the largest difference in any cell was 0.12 crashes a century, 0.4 points of mean severity and about a tenth of a point of months in recession. The 2026-09-22 retune stands.

Contagion crashes reach countries at any cycle value and are where the lift was large (a country at the cycle's floor went to 40), but the simulator does not model contagion. `test_banking_crash_no_raise.py` is the standing guard: it runs the script itself, every option of events .6 and .7, over a grid of cycle states, with a negative control that fails the old reset.

**Reproduce the headline table:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 100 --points 0,5
```

---

## 18. Lifting a tool only once its reason has gone (2026-10-05)

**Question (owner).** Switching a tool on or off has a cost. The AI should never lift an intervention until the
conditions that prompted it have changed: a buffer bought in a boom stays until the boom is over.

**What shipped.** `banking_ai_hold_cb_<tool>` in `banking_policy_triggers.txt`, one per market tool except moral
suasion. Each `cb_disable_*` ends its `ai_chance` with `multiply = 0` while its hold is true, so a lift can only
score once the hold has gone. A hold covers the enable button's core trigger, less the states its own avoid terms
rule out, and reaches past it so that a cycle sitting on a phase edge cannot flip the tool:

| Tools | Held while |
|---|---|
| Buffer, reserve requirements, margin requirements | no recession, and cycle 60 or more, momentum +3 or more, or stable with momentum above 0 |
| Deposit guarantee, emergency liquidity, bank holiday | panic or downturn |
| Directed credit (all five sectors) | downturn or stagnation, or stable with momentum below 0. Not a panic: the enable side vetoes one and the points go to the lender of last resort |
| Asset relief, bail-in | below 40, or stable with momentum below 0 |
| Export credit | its core (panic to stagnation, or momentum −3 or less) or asset relief's hold, with no frenzy and no bubble at risk |
| Open-market operations | its core (a slump, momentum −3 or less, or deflation), with no frenzy, no bubble at risk and inflation under the elevated edge. A tight stance lifts it whatever the hold |
| Capital controls | its core: the external crisis (full system), or panic, downturn or momentum −3 or less (simplified rule) |
| Moral suasion | no hold. Switching it costs nothing, so its disable button still frees the point in a boom or frenzy |

The external tools already lifted only while `banking_ai_core_cb_<tool>` was false. The sim ports the holds as
`ai_holds`, and counts what the AI lifts, what it buys back within twelve months of lifting it (`flips`), and how
often it lifts a tool whose own enable button still scores above zero (`wanted`).

### F26 — The simulator never saw the AI's capital controls under the full system

`te_mon_in_external_crisis` is a war or `te_mon_in_financial_crisis`, and the second includes every panic and
downturn (and a gold peg at confidence 40 or less, and inflation band 6). The port assumed it was never true with
the currency at par, so in every default-rule run since phase 1 the AI never bought controls. In game the button
scores 15 plus law and points flavour in every downturn, and 70 when a gold country's vault or peg is at stake.
Ported (`in_external_crisis`; `--tune cc_crisis=off` restores the old port), the simulated AI buys controls 4 to 8
times a century, and in two gold cells they cost crashes. Gold, 200 runs, with and without `--exclude-tool
capital_controls`:

| cell | with controls | without |
|---|---|---|
| `gold/price/2pt` | 10.0 | 7.0 |
| `gold/price/3pt` | 9.1 | 6.7 |
| `gold/growth/3pt` | 17.2 | 14.1 |
| `gold/growth/5pt` | 14.1 | 11.8 |
| `gold/nothing/3pt`, `gold/peg/3pt` | 8.8, 12.0 | 8.7, 12.3 |

Averaged over 2 to 8 points, the corrected port adds 0.8 crashes a century to gold, 0.2 to commodity and fiat, and
nothing to digital. **But no AI runs the gold cells that move** (§20, F29): every AI on a convertible gold standard
runs peg defence (`te_monetary_update_target`), and the `cb_*` buttons are AI-only, so `gold/price` and
`gold/growth` pair the AI's tool weights with a mandate only a player can set on gold. In `gold/peg`, the AI's own
gold cell, controls cost nothing. Nothing changed in script.

### F27 — Result: re-buys halve, crashes flat

200 runs × 100 years per cell, every currency and mandate, 2 / 3 / 5 / 8 points. The three columns are the script
before (`--tune pre_hold`), the corrected capital-controls port with the old lift weights (`--tune ai_hold=off`), and
shipped. Means over the cells in each row:

| cells | crashes / century | lifts | re-buys within a year | lifts while still wanted | tools held |
|---|---|---|---|---|---|
| all | 13.09 → 13.41 → 13.10 | 61.9 → 65.0 → 54.1 | 6.66 → 7.34 → 3.24 | 0.52 → 1.73 → 0.40 | 0.93 → 1.01 → 1.10 |
| no mandate | 21.40 → 21.45 → 20.83 | 76.4 → 80.1 → 70.3 | 8.29 → 8.54 → 4.92 | 1.48 → 1.85 → 1.22 | 1.01 → 1.05 → 1.15 |
| price stability | 6.10 → 6.71 → 6.53 | 50.1 → 53.2 → 40.5 | 6.88 → 7.53 → 2.60 | 0.05 → 1.24 → 0.02 | 0.82 → 0.94 → 1.03 |
| growth | 12.33 → 12.67 → 12.51 | 61.1 → 63.4 → 52.0 | 5.63 → 6.90 → 2.61 | 0.13 → 2.43 → 0.04 | 0.97 → 1.07 → 1.15 |
| peg defence | 10.92 → 11.03 → 10.79 | 54.2 → 58.0 → 52.2 | 3.36 → 3.59 → 1.54 | 0.12 → 0.43 → 0.07 | 0.91 → 0.95 → 0.99 |

Re-buys within a year, by tool, over the mandate cells:

| tool | before → port → shipped |
|---|---|
| bail-in | 1.28 → 1.22 → 0.10 |
| directed credit (Infrastructure) | 1.15 → 1.14 → 0.11 |
| export credit | 0.76 → 0.66 → 0.14 |
| asset relief | 0.58 → 0.51 → 0.03 |
| capital controls | 0 → 1.12 → 0.22 |
| buffer | 0.60 → 0.55 → 0.37 |
| moral suasion (no hold) | 0.90 → 1.02 → 1.07 |
| restrict inflows (external, unchanged) | 0.32 → 0.30 → 0.29 |

The old re-buys were mostly at an edge, not overlaps: the lifts while still wanted were near zero in the mandate
cells before. A slump tool's lift weight started at stable, so a recovery that touched 40 and dipped back lost the
tool and bought it again. The holds through stable on falling momentum remove almost all of it. The exception was
capital controls under the corrected port, lifted in a boom while still at war (1.21 a century while still wanted,
0 now). What still counts as wanted is moral suasion, which has no hold by design.

The gates alone (middle column to shipped) lower crashes in 35 cells of 52 and raise them in 13. The largest falls
are the unsteered 8-point dials, fiat 35.6 → 32.3 and digital 34.3 → 30.7, where the leaning tools now hold through
a climbing stable phase. The largest rise is `gold/growth/3pt` 16.3 → 17.2 (+0.85), and the other twelve are
+0.62 or less, against the ±0.5 noise §11 saw at 400 runs. Tools are held 18% more of the time (0.93 → 1.10),
about half of that from the port. Under the simplified rule (fiat only,
`--simplified`), crashes go 18.42 → 17.88 and re-buys 6.84 → 3.80.

**What remains.** Moral suasion is bought back about once a century, by design. The buffer's 0.37 is mostly a
crash lifting it and a fast recovery bringing it back, which is two real changes of conditions.

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 2,3,5,8 [--tune pre_hold | --tune ai_hold=off]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --only fiat --points 2,3,5,8 --simplified [--tune pre_hold]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --only gold --points 2,3,5 [--exclude-tool capital_controls]   # F26
```

---

## 19. The Bank Holiday: stop the run, then reopen (2026-10-05)

**Question (owner).** The Bank Holiday is declared in a downturn or panic, but its main line, crash chance
−90%, mostly matters in a bubble. Make it do its work in the slump it is declared in.

**Why the crash line did little.** Below cycle 40 a country's own crash weight is `(bubble − 90) × 0.01`, and
the holiday is only declared below 25, where a panic drains 7 bubble a month and a downturn 3. So the domestic
half of −90% is 90% of almost nothing. Its other half shields against crashes spreading in from trading
partners (`banking_contagion_crash_check` multiplies by the same `banking_crash_chance_multiplier_value`).
Before §17, a contagion crash in a slump *set* the cycle to its tier, 30–40 for a country with no bubble, so
the shield mostly blocked a lift. Since §17 it can only deepen a slump, so the shield stays. The simulator has
no contagion, so this half is not measured here.

**What shipped.**

- **The run stops.** Declaring the holiday sets a negative momentum to 0 (it used to halve it), and while the
  modifier is on `banking_cycle_advance_variables` keeps momentum at 0 or above, after every other push.
- **A full term reopens with a bounce.** `banking_cycle_bank_holiday_reopen`, in the monthly pulse just before the cycle advances, adds
  `banking_bank_holiday_reopen_momentum` (+1) once the 90-day modifier has expired, if
  `banking_bank_holiday_reopening` is still set. Disable, a change of economic system and a revolution all
  clear it, so ending a holiday early gives the bounce up.
- The crash line, the points, the cooldown and the radicals are unchanged.

The sim ports all of it (`--tune pre_holiday` for the old halving) and adds `--holiday`: at every entry below
cycle 25 (at most one per five years, the cooldown) it forks the run and follows each arm for 36 months on the
same random draws, with no AI tools, so nothing leans against the recovery it causes.

### F28 — The size of the bounce

At every entry below cycle 25, 200 runs × 100 years per cell. *@18* is the median cycle value 18 months after
the declaration, *60+* the share at 60 or more then, *boom* the share that reached 75 within 24 months, *crash*
the share that crashed within 36 months, and *to 40* the median months to reach stable. *Old* is the halving
alone; *freeze* is the §19 holiday with no bounce.

| cell (entries) | arm | @18 | 60+ | boom | crash | to 40 |
|---|---|---:|---:|---:|---:|---:|
| `fiat/price` (853) | none | 50.9 | 9% | 3% | 13.8% | 13 |
| | old | 52.3 | 12% | 4% | 9.5% | 12 |
| | freeze | 54.0 | 21% | 6% | 9.5% | 11 |
| | **+1** | **57.7** | **38%** | **10%** | **13.4%** | **9** |
| | +2 | 62.0 | 61% | 19% | 18.2% | 8 |
| `fiat/growth` (1348) | none | 51.5 | 15% | 9% | 22.6% | 13 |
| | old | 53.8 | 22% | 11% | 24.3% | 11 |
| | freeze | 56.5 | 33% | 15% | 24.9% | 10 |
| | **+1** | **60.5** | **53%** | **27%** | **32.9%** | **8** |
| | +2 | 65.1 | 74% | 40% | 43.5% | 7 |
| `gold/peg` (1294) | none | 44.1 | 4% | 3% | 7.9% | 16 |
| | old | 48.3 | 9% | 5% | 11.5% | 13 |
| | freeze | 52.2 | 19% | 9% | 14.7% | 11 |
| | **+1** | **56.6** | **34%** | **14%** | **20.7%** | **9** |
| | +2 | 61.3 | 55% | 24% | 30.5% | 8 |
| `commodity/nothing` (1081) | none | 41.5 | 3% | 1% | 5.9% | 18 |
| | old | 45.6 | 8% | 4% | 9.0% | 14 |
| | freeze | 48.8 | 15% | 6% | 11.5% | 11 |
| | **+1** | **52.6** | **26%** | **11%** | **16.2%** | **10** |
| | +2 | 57.0 | 39% | 17% | 22.0% | 8 |

**The freeze is the cheap half.** It brings stable two to seven months sooner than no holiday, and one to three
sooner than the old halving. The chance of another crash within three years moves less than with any bounce:
down under fiat price stability (13.8% → 9.5%), up 2 points under a growth target and 6–7 under the gold peg and
unsteered commodity money.

**The bounce buys speed with that risk.** Each point of it is worth about 4 cycle points at eighteen months and
one to two months off the climb to stable. Under fiat price stability, where the bank leans against the rebound, +1 costs
nothing (13.8% → 13.4% within three years) and +2 costs 4 points. Under a growth target or a gold peg the bank
leans less, so +1 costs 10–13 points against no holiday and +2 about 21. The owner proposed about +2; at +2 more than half
of the slumps under fiat or the gold peg stand at 60 or above at eighteen months, and a sixth to two fifths reach a
boom within two years. **+1 shipped:** the median slump stands between 52 and 61 at eighteen months, and stable
comes four to eight months sooner than with no holiday. `--holiday-bounces` and `banking_bank_holiday_reopen_momentum`
change it.

The unsteered fiat and digital dials (`*/nothing`) crash within three years after 85% or more of their slumps
whatever the holiday does, so they say nothing about the bounce. Pooled over all 13 cells, which they dominate,
the shares are much higher (no holiday 30.8%, +1 41.1%, +2 46.9%).

No arm has any other tool: in play, a player or the AI leaning against the rebound with the buffer, margin
requirements or the policy rate would take some of the bounce's risk back.

### AI centuries

The AI declares 0.9 holidays a century, the same as before, since its weights did not change. 200 runs × 100
years, every currency and mandate, 2 / 3 / 5 / 8 points, `--tune pre_holiday` → shipped: crashes 13.10 → 13.14
a century, months in recession 6.83% → 6.68%, longest slump 27.0 → 26.8 months. No cell moved by more than 0.7
crashes a century, within the noise of 200-run cells.

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --holiday --runs 200 --holiday-bounces 0,1,1.5,2
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 2,3,5,8 [--tune pre_holiday]
```

---

## 20. The AI's capital controls on gold (2026-10-05)

**Question.** §18's F26 found that once the simulator saw the AI's capital controls under the full system, they
cost gold countries 2 to 3 crashes a century in the price-stability and growth cells. Why there, and should the
AI's enable weight change?

**What shipped.** Nothing in script: the rise is in cells no AI runs (F29). The simulator gains three `--tune` keys
for the A/B below: `cc_cost=N` sets the controls' point cost (2), `cc_damp=X` the damp they put on gold flows
(`te_mon_controls_damp_value`, 0.25), and `cc_weak=X` the enable weight for an external crisis with nothing at stake
(15; at 0 the law and points flavour goes with it, as it would if the core trigger narrowed to match).

### F29 — The rise is in cells no AI runs

Two pieces of script decide which gold cells belong to an AI:

- `cb_capital_controls_outflow` is `visible = { is_ai = yes … }`. A player sets controls from the dashboard, and no
  AI weight clicks for them.
- `te_monetary_update_target` gives every AI on a convertible gold standard the peg-defence mandate, whatever its
  wars and debt.

So the AI's controls on gold are the `gold/peg` cells alone. The `gold/price` and `gold/growth` cells pair the AI's
tool weights with a mandate only a player can set on gold. They also lack the AI's vault top-up (step 10 of
`te_monetary_update_gold`: a tenth of the limit a month while the vault is under a quarter and the treasury over
half), which the simulator does not port. In the peg cells controls cost nothing (400 runs × 100 years):

| cell | crashes / century, with controls → without | controls bought / century | re-bought within a year |
|---|---|---|---|
| `gold/peg/2pt` | 12.60 → 12.88 | 5.49 | 0.13 |
| `gold/peg/3pt` | 12.01 → 12.31 | 3.58 | 0.09 |
| `gold/peg/5pt` | 10.73 → 10.60 | 4.79 | 0.13 |
| `gold/peg/8pt` | 8.19 → 8.03 | 4.24 | 0.10 |

The differences are inside the noise: a peg cell's runs have a standard deviation of 2.9 crashes, so two standard
errors of a difference at 400 runs are about 0.4. A peg-defence bank sets its rate at the world rate plus half its
reserve shortfall, rounded up, so its gold flows net to zero or run inwards. The vault never falls under the 10%
pressure floor, peg confidence never reaches 40 (no month in 100 runs per cell, 2 to 8 points), and the 70 never
fires. Every purchase is the 15 for a crisis with nothing at stake: a war (half to two thirds of the months held) or
a recession. `cc_weak=0` therefore gives the same crashes as excluding the tool, run for run. The same holds in
`gold/nothing`, where the unsteered rate sits on or above the world rate.

### F30 — Where the 70 does fire, a doubted peg keeps controls on through the boom and starves the leaning tools

This matters for a player on gold who delegates to price stability or growth and buys controls, and for the AI if
its gold mandate rule ever changes. With no controls at 3 points, the rate sits under the world rate in 33% of
months under price stability and 45% under growth (three quarters or more of recession months, the cycle lean),
and the vault is under the pressure floor in 27% and 49% of months. Peg confidence is at 40 or below in 33% and 55%
of months, more often in expansion, boom and frenzy (55% to 78% of those months) than in a recession. Under peg
defence each of these is 0%. Measured at 3 points over 100 runs:

1. **The peg leg buys them at 70.** A peg at 40 or below makes `te_mon_in_external_crisis` true and also counts as
   "at stake". It accounts for 5.4 of 6.8 purchases a century under price stability and 3.4 of 4.7 under growth,
   most of them in the stable phase.
2. **The hold keeps them through the boom.** The hold is the core trigger, so controls stay on while confidence
   stays at 40 or below: through 64% to 82% of expansion, boom and frenzy months. In those months the AI has 0.4
   points free and holds no leaning tool, against 0.5 to 0.6 on average in hot months without controls.
   Countercyclical buffer purchases fall from 6.7 to 2.0 a century (price) and from 11.3 to 2.4 (growth).
3. **The damp prolongs the doubt.** Quartering the inflow slows the vault's refill, so with controls confidence
   is at 40 or below in 41.5% of months, against 34.3% with `cc_damp=1` and 33.2% with no controls (growth 60.9 /
   53.5 / 55.2), and controls are held in 39.9% of months against 32.4% (growth 59.8 / 52.8). The damp does not
   loosen the boom's stance: in hot months with controls on the clamped stance gap is +0.30 with the damp and
   +0.19 without.

Which part costs the crashes, 200 runs × 100 years. The last column is buffer plus reserve-requirement purchases
a century, as shipped / with no controls / with free controls:

| cell | as shipped | no controls | free (`cc_cost=0`) | no damp (`cc_damp=1`) | free, no damp | leaning purchases |
|---|---|---|---|---|---|---|
| `gold/price/2pt` | 10.0 | 7.1 | 9.7 | 8.8 | 8.0 | 2.0 / 5.2 / 6.1 |
| `gold/price/3pt` | 9.1 | 6.7 | 7.8 | 8.4 | 7.1 | 2.0 / 6.7 / 7.2 |
| `gold/price/5pt` | 7.3 | 6.1 | 5.9 | 6.3 | 5.2 | 9.2 / 12.7 / 12.3 |
| `gold/price/8pt` | 5.0 | 5.0 | 4.3 | 4.8 | 4.1 | 14.2 / 15.5 / 14.3 |
| `gold/growth/2pt` | 16.2 | 14.6 | 14.5 | 16.4 | 15.0 | 2.1 / 8.8 / 8.7 |
| `gold/growth/3pt` | 17.2 | 14.1 | 14.5 | 16.1 | 14.9 | 2.4 / 11.3 / 11.8 |
| `gold/growth/5pt` | 14.1 | 11.8 | 12.0 | 13.7 | 11.2 | 13.6 / 20.0 / 21.5 |
| `gold/growth/8pt` | 10.5 | 8.6 | 9.2 | 10.4 | 8.5 | 23.4 / 20.9 / 22.6 |

Under growth the points are the cost: free controls give back the leaning tools and almost all of the crashes.
Under price stability the points and the damp share it, and the cells are noisy: a run's crashes spread from 1 to
20 a century (standard deviation 6.7), so one standard error of a difference is about 0.7 at 200 runs. Dropping
the 15 does not reach any of this, because it is the 70 that buys these controls: at 400 runs, `cc_weak=0` moves
the eight cells by −1.2 to +0.2 (price 2pt 10.29 → 9.81, growth 3pt 17.44 → 16.21), against 0.0 to −3.2 for no
controls at all.

### Result — the AI's own cells, 200 runs × 100 years, 2 / 3 / 5 / 8 points

The cells an AI can be in: gold under peg defence, every other currency under price stability or growth (the AI's
growth mandate is for war or debt at half its credit limit, so a whole century of it overstates it). Means over the
four budgets, as shipped → `--exclude-tool capital_controls`. **crashes** is crashes a century; **controls bought**
and **controls re-bought** (within twelve months of a lift) are capital-controls clicks a century as shipped;
**lifts**, **flips** and **wanted** are §18's columns over every tool: lifts a century, re-buys within a year of a
lift, and lifts made while the tool's own enable button still scored above zero.

| cells | crashes | controls bought | controls re-bought | lifts | flips | wanted |
|---|---|---|---|---|---|---|
| `commodity/price` | 6.23 → 6.30 | 3.28 | 0.07 | 38.7 → 36.9 | 2.09 → 2.02 | 0.00 → 0.00 |
| `commodity/growth` | 10.38 → 10.33 | 3.82 | 0.09 | 48.7 → 46.7 | 1.89 → 1.83 | 0.01 → 0.01 |
| `gold/peg` | 10.79 → 10.97 | 4.53 | 0.12 | 52.3 → 50.6 | 1.54 → 1.42 | 0.07 → 0.07 |
| `fiat/price` | 6.60 → 6.43 | 3.29 | 0.04 | 41.9 → 39.8 | 2.43 → 2.34 | 0.03 → 0.02 |
| `fiat/growth` | 13.16 → 12.99 | 4.10 | 0.08 | 58.1 → 55.8 | 2.52 → 2.46 | 0.05 → 0.06 |
| `digital/price` | 5.43 → 5.48 | 3.06 | 0.06 | 41.7 → 39.7 | 2.96 → 2.91 | 0.04 → 0.03 |
| `digital/growth` | 12.04 → 12.27 | 3.91 | 0.06 | 57.0 → 55.5 | 3.27 → 3.33 | 0.06 → 0.09 |
| `fiat/price`, `--simplified` | 6.20 → 6.14 | 1.62 | 0.01 | 36.5 → 35.8 | 2.11 → 2.07 | 0.03 → 0.03 |
| `fiat/growth`, `--simplified` | 12.57 → 12.51 | 3.01 | 0.01 | 51.1 → 50.0 | 2.11 → 2.15 | 0.04 → 0.04 |

Across the seven default-rule rows the AI's controls change crashes by −0.02 a century on average, and no row by more
than 0.23; the simplified rule's rows by 0.06. Every default-rule purchase in these cells is the 15, so `cc_weak=0`
reproduces the "without" figures exactly. The cells no AI runs move as F26 reported: the unsteered dials by 0.1 or
less on average, `gold/price` 7.85 → 6.24 and `gold/growth` 14.47 → 12.26.

### What remains

- **A peg-defence AI whose confidence falls some other way.** The simulator holds the exchange rate at par, so it
  never sees confidence drained by overvaluation (`te_mon_fx_overvaluation_drain`) or knocked down by events. There
  the 70 fires and the hold keeps controls on while confidence stays at 40 or below, perhaps through a boom as in
  F30. Controls also quarter that drain, which F30's cells never exercise. Whether they then cost crashes or pay for
  their points needs the currency loop (`banking_deflation_trap.py`'s `CurrencyLoop`) inside the century simulator.
- **The vault top-up.** Porting it would only make an AI's peg sounder; it does not change F29.
- **The 15.** It buys controls three to five times a century in a war or a recession and costs nothing measurable
  in any AI cell, so it stays.

**Reproduce:**

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 400 --only gold --points 2,3,5,8 [--exclude-tool capital_controls | --tune cc_weak=0]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --only gold --points 2,3,5,8 {--tune cc_cost=0 | --tune cc_damp=1 | --tune cc_cost=0,cc_damp=1}   # F30's decomposition
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 2,3,5,8 [--exclude-tool capital_controls | --tune cc_weak=0]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --only fiat --points 2,3,5,8 --simplified [--exclude-tool capital_controls]
```

---

## 21. Cooperative Ownership, measured for the first time (2026-10-05)

In play, cooperative economies boomed and crashed a lot. The simulator runs a market economy only (§1 leaves the `cw_*` tools out, and §3 left the `_coop` phases "unmeasured"), so this section uses an **interim cooperative arm**: a monkeypatch of `banking_cycle_sim.py`, posted on [#720](https://github.com/jakeOmega/Vic3TimelineExtended/issues/720), which tracks folding a command and a cooperative arm into the simulator properly. It reads the `_coop` phase modifiers, the `bubble_inertia_*_coop` modifiers and the eight `cooperative_*` tool modifiers from the mod files, and hard-codes what the script keeps as inline literals: crash weight ×0.65 and severity ×0.8 (`banking_cycle_effects.txt`), the law's −0.25 on `country_banking_random_momentum_mult` (`construction_system_law_injections.txt`) and the `cw_*` buttons' `ai_chance` blocks with the `banking_ai_hold_cw_*` gates #716 put on their disables. 300 runs × 100 years a cell, fiat / price stability unless stated.

### What was wrong

1. **The cooperative cycle on its own was too calm.** Untooled it crashed 0.6 times a century, against 10.9 for a market economy, and spent 0.2% of months in Boom or Frenzy. It had no positive feedback: `banking_cycle_apply_phase_modifiers` gave bubble inertia to market economies only, so a cooperative economy almost never left Stable, and the cooperative boom events (`.61`, `.62`, `.64`, `.66`, `.67`) had little to fire from.
2. **Two council tools did all the booming.** Collective Capital Investment Plan carried +0.30 momentum and Cooperative Credit Union Expansion +0.25. §1's F1 explains why that is huge (a standing momentum add converges on ten times itself in cycle points a month), and §3 cut the market tools to ×0.3 for it; the council tools were never measured and kept the old scale. Together they moved the cycle +5.5 points a month, and switching them off left about 50 points of push. A player who left both on spent 28% of months in Frenzy. Under the AI the crash rate *rose* with the point budget (0.4 at 2 points, 3.6 at 6).
3. **The pool term compounded.** Each week the cooperative phases added `investment_pool × country_weekly_investment_pool_mult`: a share of the pool's balance, not of its income, so an unspent pool grew ×1.68 a year in Frenzy (+0.01 a week) and halved in a year of Panic. Market phases move the capitalists' contribution instead, a flow. `mod_systems.md` § Overinvestment already named it as one way an Overinvestment episode runs on indefinitely.

Ruled out: the coop-only events (`.60`–`.67`: one-off ±1–2 momentum, ±3–8 bubble) and the cooperative −0.5pp on the neutral rate, which, if anything, tightens the stance.

### What shipped

| change | where |
|---|---|
| Capital Plan momentum 0.30 → **0.10**, Credit Union Expansion 0.25 → **0.08** (the market tools' scale: Open Market Operations 0.10, Emergency Liquidity 0.08) | `cooperative_capital_plan`, `cooperative_credit_expansion` |
| `country_weekly_investment_pool_mult` is a share of the pool's weekly **gross income** (clamped at 0), not of its balance, and may not take more than the pool holds. The six phase values and `neocolonial_dependency_imposed_modifier` ×24: Panic −0.36, Downturn −0.18, Stagnation −0.072, Expansion +0.072, Boom +0.144, Frenzy +0.24 | `investment_pool_banking_cycle_income_add`; the `_coop` phases |
| **Cooperative bubble inertia** at a fifth of the market's: `bubble_inertia_{moderate,high,extreme}_coop` (0.2 momentum, under the same bands and `bubble_inertia_multiplier_script_value`) | `banking_cycle_apply_phase_modifiers`, `remove_all_banking_phase_modifiers` |

×24 keeps each phase's pool effect the same size at the pool a country settles at when the private queue spends a 24th of it a week (24 weeks of income); above that pool the old term was larger, which was the problem. Gross income leaves this script add out (`ce_treasury_pool_balance_multiplier`'s note), so the term cannot feed on itself, and Overinvestment cuts every pop's contribution and gross income with it, so the cycle no longer prolongs Overinvestment.

The inertia share was chosen to put an untooled cooperative economy at **about 2 crashes a century**, the owner's target ("very slightly higher, but closer to this than 6"). The levers that only scale crashes did not get there (a 300-run sweep on other seeds, 0.8 untooled at baseline with the tool cut in): crash weight ×0.65 → ×1.0 moved untooled crashes 0.8 → 1.0, the law's volatility −0.25 → 0 moved them 0.8 → 0.7, Expansion's bubble add 2.5 → 4 moved them to 1.0, because a cycle that never leaves Stable gives a crash roll nothing to act on. Inertia at ×0.15 / ×0.2 / ×0.25 / ×0.5 gave 1.8 / 2.2 / 2.7 / 5.8 (200–300 runs).

### Results

Measured on `main` after #716.

**AI picks the tools, fiat / price stability** (300 runs × 100 years a cell; crashes a century, with the share of months in Boom or Frenzy):

| points | market | cooperative before | cooperative after |
|---|---|---|---|
| 0 | 10.9 (9.0%) | 0.6 (0.2%) | **2.0** (0.8%) |
| 2 | 8.5 (7.8%) | 0.4 (0.2%) | **1.2** (0.8%) |
| 4 | 6.4 (6.7%) | 2.0 (6.1%) | **2.3** (2.4%) |
| 5 | 5.3 (5.6%) | 3.1 (9.9%) | **3.0** (3.6%) |
| 6 | 4.7 (5.6%) | 3.6 (12.7%) | **3.1** (3.4%) |
| 8 | 3.8 (5.0%) | 3.0 (15.8%) | **1.8** (3.9%) |

**A player who leaves the tools on all game** (8 points; the pool column is the toy pool's median peak / trough against its settled level, with the private queue's spending capped at 1.2× income):

| tools held | crashes/century | Boom+Frenzy | Frenzy | pool peak / trough |
|---|---|---|---|---|
| market: Open Market Ops + Directed Credit | 14.8 | 9.8% | 1.3% | 1.20 / 0.66 |
| cooperative before: Capital Plan | 20.5 | 29.0% | 5.1% | 1.33 / 0.86 |
| cooperative before: Capital Plan + Credit Expansion | 39.2 | 42.7% | 27.8% | 1.62 / 0.82 |
| cooperative after: Capital Plan | 8.1 | 6.1% | 0.2% | 1.14 / 0.87 |
| cooperative after: Capital Plan + Credit Expansion | 17.4 | 18.4% | 2.4% | 1.21 / 0.74 |

**Other currencies and dials** (200 runs; crashes a century at 0 / 4 / 8 points, AI picks the tools):

| cell | market | cooperative before | cooperative after |
|---|---|---|---|
| gold / price stability | 7.8 / 7.7 / 5.2 | 1.4 / 2.9 / 4.8 | 2.9 / 2.7 / 3.2 |
| commodity / price stability | 9.2 / 5.8 / 3.6 | 1.4 / 2.2 / 4.2 | 3.3 / 2.4 / 2.5 |
| fiat / growth | 18.3 / 13.0 / 9.5 | 5.1 / 4.6 / 7.3 | 8.6 / 5.4 / 4.9 |
| gold / dial never touched | 9.7 / 7.7 / 5.4 | 5.9 / 7.7 / 9.6 | 7.4 / 7.0 / 7.3 |
| fiat / dial never touched | 35.1 / 35.6 / 32.5 | 33.1 / 32.2 / 24.2 | 33.8 / 32.9 / 25.5 |

Digital / price stability, cooperative after (300 runs): 1.5 / 2.1 / 1.3. The fiat "dial never touched" row is the passive-fiat case of §3–§4, set by the monetary dial rather than the economy (players are delegated by default since then); the change leaves it where it was.

**With the aggregate event stand-in** (`--event-channel`, 300 runs, fiat / price, 0 / 4 / 8 points): market 13.3 / 8.0 / 4.5, cooperative after 2.7 / 2.5 / 1.9. The events add 0.1–0.7 crashes a century to a cooperative economy, against 0.7–2.4 to a market one.

### Reproduce

The interim arm posted on #720, run from the repo root (the cross-currency rows use its `cell()` helper with `before=True` / `False`):

```
python3 path/to/coop_probe.py --runs 300
```

## 22. Imported crashes as an independent channel (#717)

The simulator now accepts `--imported-crash-years N`, default **0 (off)**. Each month an arrival
is drawn with probability `1 / (12 × N)`; N must be at least one month when enabled. This is a
geometric monthly waiting time, the discrete Poisson stand-in recommended in #717. It represents
an overseas crash that already reached this country: the reach roll and seven-day event delay are
folded into N. Foreign severity is drawn uniformly from the five tier midpoints, 10/30/50/70/90.
That fixed mix keeps the arrival channel independent of the local bubble tuning.

The arrival then runs the script's crash/scare lottery: `(bubble + boost) × chance multiplier`,
against weight 100. The foreign-severity boost is 5/10/20/30; a crash's severity seed is
`bubble × banking_crash_severity_scale_value + 5/10/15/20`, multiplied by the same 0.5–2 lottery
as an origin crash and by the recipient economy's damping, then capped at 100. Both paths use the
same tier-ceiling helper and clear the bubble only on a crash. Scares lower cycle/momentum by
3/1 in a market economy, 1/0.5 under command and 2/0.5 under cooperative ownership; their floor
clamps cannot lift either figure above its prior value.

`State.imported_crashes` and `imported_scares` record arrival month, foreign severity, local severity,
prior state, tier and actual drops. They never enter `State.crashes` or start an origin recovery
clock. The extra summary reports both populations' counts per century and mean drops, plus the
share of imported crashes whose recipient was already below the tier ceiling. Origin crash count,
severity, depression share, recovery and post-crash stance still use origin records; imports can,
of course, change the subsequent path and therefore an origin's eventual recovery time. An imported
crossing is excluded from the count of downturns attributed to policy alone.

**Measured:** 100 runs × 100 years per cell, fiat / price stability, seed 20260922, 10-year mean
arrival interval. These are sensitivity samples, not new origin-crash tuning targets.

| economy / points | origin crashes/century | imported crashes/century | scares/century | already below tier | crash value / momentum drop | scare value / momentum drop |
|---|---:|---:|---:|---:|---:|---:|
| market / 0 | 9.80 | 2.05 | 8.14 | 7.3% | 31.07 / 2.55 | 2.95 / 1.00 |
| market / 8 | 3.73 | 2.12 | 7.68 | 0.9% | 27.81 / 2.03 | 3.00 / 1.00 |
| command / 0 | 0.89 | 1.20 | 8.69 | 1.7% | 22.29 / 1.57 | 1.00 / 0.50 |
| command / 8 | 1.05 | 0.40 | 9.29 | 5.0% | 32.07 / 0.83 | 1.00 / 0.50 |
| coop / 0 | 1.68 | 1.91 | 8.29 | 4.7% | 23.21 / 1.90 | 1.99 / 0.50 |
| coop / 8 | 1.57 | 1.58 | 8.33 | 3.8% | 28.63 / 1.69 | 2.00 / 0.50 |

Even with the fixed 10-year arrival interval, the crash/scare split depends on local bubble pressure
and protection. At zero points, imports replace some future origin crashes by clearing the bubble
and lowering the cycle sooner. Adding origin and imported counts would hide that distinction.
The 1–7% of imported crashes landing below their tier are the population §17 could not measure;
the ceilings ensure they cannot raise the cycle.

**Deliberate omissions:** crisis-wave cascades, the Great Depression chain, effective-backstop ×0.8,
and contagion event-option modifiers, including Option A's decaying protectionism. These tables use
the bare imported effects. `--event-channel` remains a separate optional aggregate event stand-in.
No new random draw is consumed with imports off. With all extensions off, both the printed market
table and JSON retain their earlier shape; a fixed-hash-seed regression compares the JSON byte for
byte against main `028ea9cf`. `test_banking_sim_extensions.py` checks the entire ceiling/scare grid
against the real script's interpreter and the crash/scare weights and severity lottery against an
independent interpreter of `banking_contagion_crash_check`.

Reproduce the price-stability rows from these CLI outputs (which also print the other fiat dials):

```bash
for economy in market command coop; do
  PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py \
    --runs 100 --years 100 --seed 20260922 --only fiat --points 0,8 \
    --economy "$economy" --imported-crash-years 10 --pool --jobs 4
done
```

## 23. Permanent command and cooperative arms (#720)

`--economy market|command|coop` now selects the phase modifiers by their suffix, the cooperative
inertia family (none under command), and the economic-law volatility modifier from the
`INJECT:law_*` blocks. Market remains the default. Origin and imported chance/severity damping
now live in four named script values shared by the game and simulator; this refactor retains the
same game values. Command economies have the script's administered 3% policy rate, zero inflation,
and no monetary stance; cooperative neutral rates include the script's −0.5pp term.

The eight planning and eight council tools read their modifiers and point costs from the mod. All
32 enable/disable weights, the 13 hold gates, and the two command transfer buttons are evaluated
from the actual script blocks through a small reader that rejects unsupported instructions.
`test_banking_sim_extensions.py` checks all 34 registered buttons against the modeled roster and
compares their toggle weights and hold gates over a state grid with an independent interpreter.
`--tune ai_hold=off` applies to these arms too. As with the market study, tech unlocks are assumed
available and the click cadence is the simulator's `--no-click-weight` assumption; radicals,
loyalists and political feedback are not modeled.

`--hold-tools cw_capital_plan,cw_credit --points 8` holds those player tools throughout the run and
disables AI clicks. Full alternate button names are accepted as aliases. The selected tools must
belong to the economy and fit the point budget; unspent points can still afford an origin crash
response. This arm keeps the player's selected tools on after a crash. It does not model switching
costs or treasury exhaustion for market tools. Existing `--rescue` and `--holiday` fork studies
remain market-only and reject combinations with these extensions.

### The optional pool

`--pool` advances 52 weekly ticks per year, distributing four or five across each month. Units are
baseline weekly gross income, the initial/settled balance is 24, and private spending is
`min(pool / 24, cap)` with cap 1.2 by default (`--pool-spend-cap`). The market toy assumes half of
inflow comes from capitalists at a 30% base contribution and applies the phase/tool contribution
adds, as the interim probe did. Cooperative and command baseline inflow is one. The cooperative
income share and its withdrawal floor are evaluated from `investment_pool_banking_cycle_income_add`,
so losses cannot take more than the balance. These are model assumptions; contribution behavior,
construction prices, queue capacity and GDP feedback from construction are not simulated.

Command net-income balancing reads `ce_treasury_pool_balance_multiplier` monthly and after a
transfer, then applies its pool add and paired treasury expense weekly. Treasury starts from the
simulation's gold-reserve assumption and also pays the exogenous deficit. Transfer buttons use
their actual cash thresholds, GDP-scaled amount/floor, pool cap and AI weights; balances are scaled
by `--pool-weekly-income` (default 1000 cash units). The default proxy still uses exogenous debt for
`in_default`, not a complete government credit model. Changing that cash scale can change transfer
frequency. Zero points means no AI clicks, including transfers. The summary reports median weekly
peak/trough relative to the settled balance, months above 1.5×, final treasury and transfer counts.
Command pool extremes below are sensitive to that toy treasury and transfer channel. The pool adds
no random draws or feedback to the market/cooperative cycle; command transfers can change AI click
selection when the pool is enabled.

### Measured arms and targets

**100 runs × 100 years**, fiat / price stability, seed 20260922, imports off, pool on with the default
cap and cash scale. The cooperative target is approximately **2 untooled crashes per century**,
per the owner's ruling recorded in #720. The command target is **unset**; these measurements do not
retune its tools or phases. Small differences from §21's interim monkeypatch reflect sample size,
seeds, the cooperative neutral-rate term and the permanent pool's 52-week calendar.

| economy / points | origin crashes/century | Boom + Frenzy | Frenzy | pool peak / trough | months above 1.5× |
|---|---:|---:|---:|---:|---:|
| market / 0 | 11.81 | 10.2% | 1.0% | 1.21 / 0.65 | 0.0% |
| market / 4 | 6.58 | 7.2% | 0.2% | 1.15 / 0.73 | 0.0% |
| market / 8 | 3.80 | 4.9% | 0.1% | 1.15 / 0.89 | 0.0% |
| command / 0 | 1.50 | 0.0% | 0.0% | 1.00 / 1.00 | 0.0% |
| command / 4 | 0.40 | 11.0% | 0.4% | 2.68 / 0.00 | 23.1% |
| command / 8 | 1.07 | 28.9% | 3.9% | 2.69 / 0.00 | 24.3% |
| coop / 0 | 2.06 | 0.9% | 0.0% | 1.11 / 0.88 | 0.0% |
| coop / 4 | 2.04 | 2.0% | 0.0% | 1.13 / 0.88 | 0.0% |
| coop / 8 | 1.68 | 4.0% | 0.0% | 1.14 / 0.93 | 0.0% |

**Player tools held all game, 8-point budget**, same run settings:

| tools | origin crashes/century | Boom + Frenzy | Frenzy | pool peak / trough |
|---|---:|---:|---:|---:|
| command: ce_allocation | 31.69 | 46.0% | 30.3% | 1.00 / 1.00 |
| command: ce_allocation + ce_distribution | 37.68 | 49.5% | 39.9% | 1.00 / 1.00 |
| coop: cw_capital_plan | 7.98 | 6.1% | 0.3% | 1.14 / 0.86 |
| coop: cw_capital_plan + cw_credit | 16.92 | 17.6% | 2.2% | 1.21 / 0.72 |
| market: omo + directed | 13.49 | 8.9% | 1.1% | 1.20 / 0.65 |

The cooperative untooled arm meets the stated target. Its held-tool arms reproduce the distinction
§21 found between AI selection and a player keeping stimulus on. The command arm confirms #720's
open concern: Emergency Allocation alone at +0.30 standing momentum produces 31.69 crashes per
century and 30.3% of months in Frenzy; adding Distribution Upgrade (+0.25) takes those to 37.68 and
39.9%. The command AI avoids most of those crashes, but spends much more time in Boom/Frenzy as
points increase. A command-tool retune needs a target for both crash frequency and phase occupancy;
this implementation makes those quantities measurable without choosing that target.

Reproduce the AI and held rows from the price-stability rows of these outputs:

```bash
for economy in market command coop; do
  PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py \
    --runs 100 --years 100 --seed 20260922 --only fiat --points 0,4,8 \
    --economy "$economy" --pool --jobs 4
done
PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py --runs 100 --years 100 \
  --seed 20260922 --only fiat --points 8 --economy market --hold-tools omo,directed --pool --jobs 4
PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py --runs 100 --years 100 \
  --seed 20260922 --only fiat --points 8 --economy command --hold-tools ce_allocation --pool --jobs 4
PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py --runs 100 --years 100 \
  --seed 20260922 --only fiat --points 8 --economy command --hold-tools ce_allocation,ce_distribution --pool --jobs 4
PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py --runs 100 --years 100 \
  --seed 20260922 --only fiat --points 8 --economy coop --hold-tools cw_capital_plan --pool --jobs 4
PYTHONHASHSEED=0 python3 scripts/analysis/banking_cycle_sim.py --runs 100 --years 100 \
  --seed 20260922 --only fiat --points 8 --economy coop --hold-tools cw_capital_plan,cw_credit --pool --jobs 4
```

---

## 24. The gold peg's deep-slump drain (2026-10-05)

**The question.** An AI-only observer game to 2015 left 124 of 175 countries on gold, some of them
in slumps that lasted years with Peg Confidence at 100. Peg defence follows the world rate and
ignores the domestic cycle (design §6); when a slump drags the neutral rate under the world rate the
stance stays Tight, momentum stays negative, and nothing ends it, because confidence fell only when
the vault was nearly empty and peg defence keeps the vault full. The fix (design §0.13) drains
`te_peg_confidence` by `te_mon_peg_slump_drain` (3) a month, and holds the recovery, while
`te_mon_peg_in_deep_slump` holds: a Downturn or Panic with `te_mon_stance_band` 4 or 5. This section
picks the definition and the size, and asks how often it fires in an ordinary century.

**What was ported.** `monetary_update_gold` gains the drain and the hold on the heal
(`--tune slump_drain=0` is the script before it), and `te_peg.1` behind its 24-month cooldown,
resolved as *Defend* (its default option: the world + 4 floor for a year, confidence +40), but only
with `Config.peg_crisis`, so the century matrix's gold cells read as before. `--tune slump_def=`
`tight` (shipped), `very_tight`, `sustained` (Tight, with step 8b's stance counter — ported for
this — at 6 or more, as §13's Dear Money Politics needs), `deflation` or `either` makes another
candidate the active one.
`--tune growth_fb_scale=N` sets `--growth-feedback`'s invented coefficient (1.5).

**The fidelity limit.** In game the standing tight gap comes from the growth term: a slump cuts
trailing GDP growth, the term reaches −1.5, and the neutral rate falls under the peg. This simulator's
growth is an AR(1) that ignores the cycle unless `--growth-feedback` is on, and its coefficient is
invented, so it cannot reproduce that case; the three arms below bracket it and the strong one (6) is
a sensitivity read, not a measurement. What it does measure well is the false-positive rate: how
often an ordinary century's downturns trip the condition.

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --peg-slump --runs 400
.venv/bin/python scripts/analysis/banking_cycle_sim.py --peg-slump --runs 200 --peg-slump-cells peg:2 --tune slump_drain=2   # and =4
```

**How often each candidate holds** (% of months, gold with a bank on peg defence, 2 points, drain off,
400 centuries an arm):

| growth coupling | Tight (shipped) | Very Tight | sustained Tight | Deflation | Tight or Deflation | Downturn + Panic |
|---|---:|---:|---:|---:|---:|---:|
| none (default) | 3.16 | 0.91 | 2.38 | 1.45 | 3.38 | 9.9 |
| 1.5 | 3.61 | 1.27 | 2.86 | 2.03 | 3.87 | 10.1 |
| 6 | 5.94 | 3.50 | 5.19 | 4.11 | 6.10 | 12.1 |

**What the drain does** (same cells; `te_peg.1` a century, of which first falls from a peg at 95 or
more, and the median months from that 95 to the crisis):

| growth coupling | drain | crises / century | first falls / century | runs with one | months from 95+ | crashes / century |
|---|---|---:|---:|---:|---:|---:|
| none | off | 0 | 0 | 0% | — | 12.8 |
| none | **Tight, 3** | **0.61** | **0.21** | 19% | 26 | 12.7 |
| none | Very Tight, 3 | 0.31 | 0.10 | 10% | 26 | 12.8 |
| none | sustained Tight, 3 | 0.58 | 0.20 | 18% | 26 | 12.7 |
| none | Deflation, 3 | 0.52 | 0.21 | 20% | 26 | 12.8 |
| 1.5 | off | 0 | 0 | 0% | — | 12.4 |
| 1.5 | **Tight, 3** | **1.27** | **0.28** | 26% | 26 | 12.3 |
| 6 | off | 0 | 0 | 0% | — | 11.9 |
| 6 | **Tight, 3** | **4.24** | **0.47** | 43% | 26 | 11.3 |

Drain 2 and 4 on the shipped condition (200 centuries an arm): 0.28 / 0.91 / 3.21 and 1.24 / 1.95 /
6.04 crises a century for the three couplings.

**Reading it.**

- **A crisis from a trusted peg comes only after two unbroken years of deep slump**: 26 months in
  every arm, which is ⌈(95 − 20) / 3⌉. The condition rarely flickers once it starts, so the drain
  behaves like the design table (27 months from 100) rather than a slow leak through ordinary
  downturns.
- **In an ordinary century it fires about once in five centuries from trust** (0.21) and in 19% of
  runs at all. The repeats, which take the total to 0.61, are the port always choosing *Defend* in a
  slump Defend cannot end: its +40 lasts about 13 months against −3, and the cooldown sets the next
  one at 24. In game an AI also suspends or devalues, so these are an upper bound.
- **Tight is the leg that matters.** A fixed nominal rate in deflation reads Tight already, so the
  Deflation band adds 0.2 points of months to it and, alone, catches downturns the peg is not
  prolonging. Very Tight alone halves the rate but would let a gap that reads 1.9 one month and 2.1
  the next drain every other month. Requiring six months of Tight first changed almost nothing.
- **Crash rates do not move** (within 0.1 to 0.6 a century, inside noise at this sample).

**Found on the way, not changed.** The port also makes the vault road visible. A gold country whose
bank runs **Price Stability** — the mandate a player's bank is seeded with — reaches `te_peg.1`
about 15 times a century (4.6 of them from a trusted peg, six months after it starts falling),
with or without the drain: its mandate cuts below the world rate in every slump and empties the
vault. Its stance in a slump is loose, so the drain never applies to it. The AI always runs peg
defence and is unaffected. Reported to the owner with the drain (design §0.13); nothing here
changes it.

---

## 25. Emergency liquidity, bounded to its crisis (2026-10-07)

**Question (owner).** Should the Emergency Liquidity Program have a timeout like the Bank Holiday, for fun
and realism? Not a calendar term: a bank holiday ends because no government can keep the banks shut, but a
lender of last resort ends when the banks stop borrowing at its penalty rate, which is when the crisis ends,
however long that takes. The holiday's other two bounds, a phase gate and one use per crisis, belong on it.

**What was wrong.**

- It opened in any phase, so it could be held through a boom as a standing −0.8pp cut to the risk premium.
- Its announcement, +12 cycle value and +10 bubble pressure at once, landed on every opening, and closing
  refunds 1% of GDP of the 1.2% it costs. An open-close round trip bought +12 cycle value for 0.2% of GDP, as
  often as the player clicked: three in a Panic took the cycle from 5 to 41 in one day.
- Nothing closed it but the player. Left open, its +0.8 bubble pressure a month fed every later boom (the
  player rows below).
- The simulator never ported the announcement, so §7, §8 and §18 measured the tool without it.

**What shipped.**

- `banking_possible_cb_emergency_liquidity_program` requires `banking_cycle_is_recession` (a Downturn or
  Panic), behind `banking_eliq_phase_tt`, as the holiday does.
- `banking_effect_cb_emergency_liquidity_program` lands the announcement only without
  `banking_eliq_announced`, and sets it. Otherwise the button's tooltip says the market has already heard it
  (`banking_eliq_announcement_spent_tt`).
- `banking_cycle_eliq_wind_down`, in the monthly pulse after the crash check, counts the months the cycle holds
  at 40 or above in `banking_eliq_recovery_months` while the program or the announcement is outstanding; any
  month below 40 restarts it. At `banking_eliq_wind_down_months` (12) it closes an open program through the
  Disable action's own effect (history marker, 1%-of-GDP refund), posts `banking_eliq_wound_down_notice` to a
  human player, and clears both variables, so the next crisis gets its announcement. Both are variables, so a
  revolution's winner inherits the spent announcement along with the crisis. A save with the program open
  from before this change has no announcement variable; it is wound down the same way.

**The port.** `on_tool_enabled` lands the announcement once per crisis, `tool_possible` carries the gate, and
`eliq_wind_down` runs after the crash check. `--tune pre_eliq_bounds` is the script before (any phase, an
announcement on every opening, no wind-down); `--tune eliq_oneshot=off,eliq_bounds=off` is the port before (no
announcement either). `--player-eliq` replaces the AI with a player who opens the program whenever it can be
opened and never closes it by hand. A held tool (`--hold-tools eliq`) stays open whatever the cycle does, as
`prune_overdrawn_tools` already leaves it.

### F31 — The AI never meets the new bounds

Crashes a century, 200 runs × 100 years, mean over all 13 currency and mandate cells:

| arm | 4 pt | 5 pt | 8 pt |
|---|---:|---:|---:|
| port before §25 (no announcement) | 13.33 | 12.52 | 10.27 |
| script before §25 (`pre_eliq_bounds`) | 13.37 | 12.49 | 10.27 |
| **shipped** | **13.37** | **12.49** | **10.27** |

The AI opens the program 0.03 to 0.75 times a century in a cell, only in a Panic or a Downturn still falling
at −4 or faster, and lifts it from Stable. The gate never binds, the wind-down fires at most 0.01 times a
century, and no cell moves by more than 0.03 crashes between the script before and shipped. Porting the
announcement moves no cell by more than 0.39 (`fiat/nothing/4pt`, a cell at 40 crashes a century), so the
earlier sections' emergency-liquidity conclusions stand.

### F32 — A player who never closes it no longer pays for forgetting

4 points, no other tools, 200 runs × 100 years. *Never closed* opens the program at the first chance and never
closes it: under the old rules that is month 0, and it stays open all century. Under the shipped rules it
opens at every Downturn or Panic and closes itself after each recovery (open 3.8% of months, 0.6 to 3.3
openings a century).

| cell | no tools: crashes · recession % | never closed, before | never closed, shipped |
|---|---|---|---|
| `gold/price` | 8.6 · 3.8 | 18.7 · 12.4 | 9.0 · 3.0 |
| `fiat/price` | 9.4 · 3.7 | 24.7 · 15.0 | 9.7 · 3.4 |
| `digital/price` | 8.1 · 2.4 | 22.7 · 11.9 | 8.4 · 2.5 |
| `commodity/growth` | 13.7 · 4.8 | 24.2 · 14.5 | 13.9 · 4.1 |
| `gold/peg` | 13.6 · 6.7 | 23.7 · 17.5 | 14.3 · 5.0 |
| `fiat/nothing` | 40.2 · 9.2 | 40.7 · 25.1 | 40.7 · 8.9 |
| all 13 cells | 16.0 · 5.7 | 25.8 · 16.3 | 16.4 · 4.8 |

Left open, the program's bubble pressure turned into crashes: 1.6 times the untooled rate on average, 2 to 2.8
times under price stability, and nearly three times the months in a slump. Each crash looked like bad luck.
Wound down after each recovery, it costs 0.4 crashes a century against no tools and takes 0.9 points off the
share of months in a Downturn or Panic, which is what a lender of last resort is for.

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 4,5,8 [--tune pre_eliq_bounds]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 4,5,8 --tune eliq_oneshot=off,eliq_bounds=off
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 4 --player-eliq [--tune pre_eliq_bounds]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 200 --points 4 --exclude-tool all
```

---

## 26. Inflation Targeting, and what lenders believe of a mandate (2026-10-07, #799)

**Question (issue #799).** Price Stability leaned on the cycle with full weight, so it was already a dual
mandate; it is now called the Dual Mandate. The issue adds a narrow rule, Inflation Targeting: "the
inflation term, with little or no cycle lean". How much lean should it keep? And a tighter mandate "is
believed only gradually": should the mandate move the credibility anchor c, and which mandates?

**The port.** The `inflation` cells run mandate 4: the Dual Mandate's rule with the cycle lean scaled by
`te_mon_mandate_inflation_lean_weight` (`--tune it_lean=`). `mandate_cred_target` ports
`te_mon_mandate_cred_target`: +`te_mon_mandate_cred_inflation` to c for a mandate-run bank on inflation
targeting that is not metallic or state-owned, earned at `te_mon_mandate_cred_build` a month (`--tune
cred_it=`; `--tune cred_growth=` measures a Growth penalty, 0 as shipped). A run keeps one mandate all
century, so the lock and the reaction to a looser rule, both one-offs at a change, are not ported.

### F33 — Without a lean, inflation targeting trades the cycle for prices

300 runs × 100 years, 0 points, delegated (universal banking) unless marked. *IT* is inflation targeting
as shipped (lean 0, +0.1 c); *dual* is the Dual Mandate.

| cell | crashes | recession % | frenzy % | longest slump | inflation | rate | rate ≥ 10% | services |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| fiat, no wage pressure: IT | 12.4 | 9.2 | 2.0 | 24 | 2.20 | 4.89 | 0.5 | 2.4 |
| fiat, no wage pressure: IT, lean 0.25 | 12.2 | 8.1 | 1.7 | 23 | 2.23 | 4.95 | 0.5 | 2.8 |
| fiat, no wage pressure: dual | 11.1 | 7.3 | 0.9 | 23 | 2.22 | 5.08 | 0.9 | 3.5 |
| digital, no wage pressure: IT | 12.6 | 8.9 | 1.9 | 23 | 2.20 | 4.91 | 0.6 | 3.3 |
| digital, no wage pressure: dual | 10.6 | 6.0 | 0.4 | 21 | 2.21 | 5.09 | 1.0 | 4.6 |
| fiat, +1pp wage pressure: IT | 1.3 | 2.7 | 0.1 | 60 | 3.30 | 7.11 | 4.4 | −4.3 |
| fiat, +1pp wage pressure: dual | 1.0 | 0.9 | 0.0 | 84 | 3.50 | 7.44 | 8.0 | −4.7 |
| digital, +1pp wage pressure: IT | 0.7 | 2.0 | 0.0 | 54 | 3.29 | 7.16 | 5.5 | −4.1 |
| digital, +1pp wage pressure: dual | 0.5 | 0.6 | 0.0 | 68 | 3.50 | 7.48 | 8.7 | −4.3 |
| fiat, independent L9: IT | 12.6 | 9.9 | 1.8 | 22 | 2.15 | 4.80 | 0.3 | 3.2 |
| fiat, independent L9: dual | 11.4 | 7.4 | 0.7 | 21 | 2.22 | 5.04 | 0.7 | 4.4 |
| fiat, independent L9, +1pp: IT | 10.4 | 8.4 | 1.4 | 23 | 2.25 | 5.01 | 0.4 | 2.4 |
| fiat, independent L9, +1pp: dual | 9.2 | 6.1 | 0.5 | 21 | 2.32 | 5.23 | 0.8 | 3.5 |

In a calm world inflation targeting holds the same 2.2% as the Dual Mandate and pays for ignoring the
cycle: about 1.2 to 2 more crashes a century, 2 to 3 points more of months in a Downturn or Panic, two to
five times the frenzy, and a point less services output. Its rate averages 0.2pp lower. Under standing wage pressure,
where the Dual Mandate sits in §12's stagnation trap, the trade turns: the longest slump falls from 84 to
60 months (fiat) and 68 to 54 (digital), inflation from 3.5% to 3.3%, and months at a rate of 10% or more
nearly halve, for more months in recession (2 to 2.7% against under 1%). Each rule wins where the other
loses, which is what a choice should look like. A quarter of the lean recovers about half of the calm-world
recession gap and blurs that line, so the weight is 0, the issue's "little or no".

### F34 — Credibility for inflation targeting only

The +0.1 to c matters only under standing pressure. Delegated fiat at +1pp: inflation 3.40 → 3.30%, months
at 10% or more 6.5 → 4.4%, longest slump 70 → 60 months. An independent bank already anchors most of that
pressure away, so the same bonus moves its inflation 2.29 → 2.25%. In a calm world it does nothing
measurable.

A Growth penalty of −0.1 was measured and turned down. Delegated fiat at +1pp: inflation 5.03 → 5.37%, a
rate of 10% or more in 23.8 → 35.0% of months, services −1.2 → −3.2%. That is a second charge on a mandate
whose price is already its inflation, and every AI at war runs Growth. So only inflation targeting moves c,
and "a tighter rule is believed gradually" means its bonus builds over two years (0.0042 a month) while a
move off it loses the bonus at once.

```
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 300 --points 0 --only fiat [--wage-pressure 1.0] [--tune it_lean=0.25 | --tune cred_it=0 | --tune cred_growth=-0.1]
.venv/bin/python scripts/analysis/banking_cycle_sim.py --runs 300 --points 0 --only fiat --fin-law law_central_bank_independence --bank-level 9 [--wage-pressure 1.0] [--tune cred_it=0]
```
