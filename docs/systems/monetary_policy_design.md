# Monetary Policy — Design

> **STATUS: DESIGN — not implemented (phase 1 next).** Written 2026-09-19 from a design
> interview with the mod owner plus an engine-feasibility pass. Every number is a starting
> point for tuning, collected in [§21](#21-tuning-constants). Items marked **(proposed)**
> were not explicitly decided by the owner. Items marked **VERIFY IN-GAME** cannot be
> proven from files. When phase 1 ships, fold the implemented parts into
> `mod_systems.md` / `journal_entry_systems.md` and keep this file as the spec for the
> remaining phases.

This extends the Banking Cycle (`je_banking_cycle` — see `mod_systems.md` § Banking Cycle
and `journal_entry_systems.md`). Read those first.

---

## 1. Goals, non-goals, principles

**Goal.** Replace the two on/off toggles that currently stand in for monetary policy
(*Raise Policy Rate*, *Open-Market Operations*) and the *Support / Devalue Currency* pair
with a real system: a player-controlled risk-free rate, a risk premium on top of it,
inflation, a currency-regime ladder that matters, and (later) exchange rates. Make late-game
finance interesting — today a late-game great power borrows at ~0.2%.

**Design principle — tradeoffs only.** A mechanic earns a control only if reasonable players
would choose differently in the same situation. Anything with a clear right answer (even a
situational one) is automated. Consequences:

- The rate moves by **drift toward a target**, so re-tuning it monthly achieves nothing.
- Any country with a national bank can **delegate** the target to a mandate. Automation is
  never locked behind a law.
- Nothing here adds a per-click cost or cooldown; friction comes from lag, not from fees.

**Non-goals.** No nominal prices (the engine has none — §2). No private credit market. No
per-state monetary effects. No full FX system this round (sketched in §15).

---

## 2. Two engine facts that shape everything

1. **`country_loan_interest_rate_*` only prices government debt.** Vic3 has no private
   credit market; a country in surplus never feels this modifier. "Low rates are
   stimulatory" must therefore be delivered through the mod's own cycle inputs
   (`country_finance_momentum_monthly_add`, `country_bubble_pressure_monthly_add`, the
   investment-pool modifiers). The policy rate has **two outputs with the same sign**: the
   government's borrowing cost, and cycle stimulus.
2. **There is no price level.** Every number the player sees is already "real 1836
   pounds", and goods prices are *real relative prices* hard-bounded to
   [0.001×, 1.999×] base (mod `PRICE_RANGE = 0.999`). Inflation can only be a state
   variable with modifier consequences; it never rescales a displayed number. The same is
   true of an exchange rate.

Supporting facts (all verified from files unless tagged):

- Vanilla's base rate is **not a define**. It is `country_loan_interest_rate_add = 0.2` in
  the `base_values` static modifier (vanilla
  `common/static_modifiers/00_code_static_modifiers.txt:12`).
- Engine formula: `rate = (Σ _add) × (1 + Σ _mult) × [per-loan bucket] × [government-owned-debt multiplier]`.
  The last two buckets have no script hook.
- 88 grant sites touch the two interest modifiers today (46 mod, 42 vanilla). The mod's
  banking sources are **all flat `_mult`** and mostly applied in **JE scope**.
- No script trigger exposes the effective rate, principal, or credit limit. Readable:
  `scaled_debt`, `in_default`, `taking_loans`, `weeks_until_bankruptcy`, `gold_reserves`,
  `gold_reserves_limit`, `scaled_gold_reserves`, `net_fixed_income`, `total_expenses`,
  `income`, `gdp`. GUI-only: `Country.GetYearlyInterestRate`, `GetMaxCredit`,
  `GetCreditRatio`.
- The **credit limit** is defines-only (`COUNTRY_MIN_CREDIT_BASE = 100000`,
  `COUNTRY_MIN_CREDIT_SCALED = 0.5`, plus building cash reserves). It can be retuned
  *globally* in `common/defines/extra_defines.txt`, never per country — a blunt but real
  lever if realistic rates make debt too cheap.

---

## 3. Player loop and information model

A country with a national bank sees a new **Monetary Policy** block at the top of the
dashboard's existing *Monetary Policy* category
(`gui/journal_entry_widgets/banking_dashboard_widget.gui`):

| Reading | Shown as | Source |
|---|---|---|
| Policy rate (actual) | exact, 1 decimal | `te_policy_rate` |
| Target | exact integer, with − / + stepper | `te_policy_rate_target` |
| Rate the government pays | exact | `JournalEntry.GetCountry.GetYearlyInterestRate` (the engine's own number — catches every bucket script can't see) |
| Risk premium | exact, with per-source breakdown tooltip | `te_risk_premium` |
| Inflation / expected inflation (P2) | exact, 1 decimal | `te_inflation`, `te_inflation_expected` |
| **Policy stance** | **band only**: very loose / loose / neutral / tight / very tight | the bank's *estimate* of (real rate − neutral rate) |
| World rate (P3) | exact | `global_var:te_world_rate` |
| Gold flow per month, peg confidence (P3) | exact flow; confidence as a bar | — |
| Delegation | toggle + mandate selector | `te_mon_delegated`, `te_mon_mandate` |

**The neutral rate is never displayed** — nobody knows r\*, and hiding it keeps judgement
in the loop. The stance band is computed from the true gap **plus the bank's estimation
error** (§8), so the player cannot recover r\* by stepping the dial and watching the band
flip. This matches the dashboard's existing philosophy ("the player reads a bar and a band,
never the number behind it" — `common/customizable_localization/banking_dash_custom_loc.txt`).

Expected decision cadence: a handful of target changes per cycle, comparable to changing a
tax level.

---

## 4. The rate stack

```
policy_rate        drifts toward target at 1/3 pp per month           (national bank)
                   = world_rate + bankless_spread                      (no national bank)
                   = administered_rate                                 (command economy)

rate_paid_pts      = clamp( policy_rate + risk_premium
                            + expected_inflation − inflation           (phase 2)
                          , 0.5 , 60 )
```

`rate_paid_pts` is written into the engine through **one** scaled country-scope modifier
(§16). Inside the engine's own formula it becomes:

```
engine rate = ( 0.20 − 0.20 + 0.01 × rate_paid_pts + residual vanilla _add )
              × ( 1 + residual vanilla _mult ) × per-loan × government-owned-debt
```

"Residual" = the small vanilla sources deliberately left alone (§7.5). The floor on
`rate_paid_pts` is therefore a floor on Σ`_add`; the rate actually paid is that ×
(1 + residual mults). The dashboard shows the engine's own number beside ours so any
leakage is visible.

- **Dial:** integer target, 1pp steps, range by regime (§5). Drift 1/3 pp per month
  (1pp per quarter). A 5pp swing takes 15 months — reversals are slow by construction.
- **Zero lower bound:** target ≥ 0 except under digital currency. A negative policy rate
  **never reaches `rate_paid_pts`** (0.5 floor, plus premium) — it acts only through the
  stimulus channel. This is intended, not a bug.
- **Floor:** engine behaviour at a total ≤ 0 is unknown, so it is never exercised.

---

## 5. Regime ladder

Monetary policy is the intersection of four existing law groups. No new laws in phase 1.

### 5.1 `lawgroup_monetary_policy` — what the dial can do

| Law | Dial | Constraint | Extras |
|---|---|---|---|
| `law_commodity_money` | **none**, even with a national bank | pays world rate + spread | no monetisation, no QE; expected inflation pinned to 0 |
| `law_gold_standard` | target 0–15 | **gold flows** (§12). Interim before P3: target clamped to reference ±2pp | credibility: premium −1pp; expected inflation anchored at 0; deflation bias |
| `law_fiat_currency` | target 0–25 | **inflation** (§9) | monetisation lever; QE at the floor; no credibility bonus — it must be earned |
| `law_digital_currency` | target **−3**–25 | inflation | negative rates (no cash to hoard); drift twice as fast (better transmission) |
| `law_decentralized_cryptocurrency` | **none** | pays world rate + spread | fixed supply: inflation pulled toward −1%; no monetisation, no QE, no lender of last resort |

The existing volatility/minting modifiers on these laws stay. This gives each law a real
identity: gold buys credibility and cheap borrowing at the price of autonomy; fiat buys
autonomy and war finance at the price of discipline; crypto is commodity money again with
better trade modifiers.

### 5.2 `lawgroup_national_bank` and `lawgroup_financial_regulation` — who holds the dial

| State | Control |
|---|---|
| `law_no_national_bank` | No policy rate. Country pays world rate + 1pp spread + premium. |
| `law_national_bank` | Player sets the target, **or** delegates it to a mandate (§6). |
| `law_national_bank` + `law_central_bank_independence` | Mandate is **binding**. No manual target, no monetisation. In return: premium floor 0.25 (vs 0.5), premium −0.5pp, expected inflation anchors twice as fast, smaller estimation error. |

Other financial-regulation laws keep their current intervention-point / volatility / lock
roles and do not touch the dial.

### 5.3 Economic system

| System | Treatment |
|---|---|
| Market (neither of the below) | Full system. |
| `law_cooperative_ownership` | Full system; neutral rate −0.5pp (mutual credit). |
| `law_command_economy` | **Administered rate** fixed at 3%. No dial, no delegation, no gold flows. Premium still applies. *Repressed inflation* (shortage pressure instead of price rises) is sketched for a later phase, not designed here. |

### 5.4 Historical-realism notes

- **1836.** The Bank of England really did set Bank Rate, under gold (GBR starts on
  `law_gold_standard` + `law_national_bank`, `common/history/extra_history.txt:78-83`), and
  Bank Rate's job was defending convertibility — exactly the §12 constraint. The United
  States had no central bank from 1836 to 1913 and lived with market rates and panics —
  the bankless row. Most of the world had no access to London at all — the §7.2 access
  premium.
- **Interwar / Bretton Woods.** Suspending convertibility (§12.3) is the 1931 option; capital
  controls buying rate autonomy under a peg is the Bretton Woods corner of the trilemma (§15).
- **1970s–80s.** Cost-push shocks (§9.3) plus accommodation produce unanchored expectations;
  the Volcker disinflation is a deliberately *very tight* stance paid for in a downturn.
  Independence as a commitment device (§6) is the 1990s consensus.
- **Post-2008.** The floor and QE (§11).
- **Open question:** France 1836 has a national bank on commodity (bimetallic) money, and
  the Banque de France did set a discount rate. As designed it gets no dial until it enacts
  gold. If that feels wrong in play, give commodity money + national bank a narrow dial
  (world rate ±1pp).

---

## 6. Delegation, mandates, independence, AI

**Delegation** is a free toggle for any national-bank country. While delegated, the monthly
update sets the target from the mandate formula instead of the player's stepper.

| Mandate | Target formula (clamped to the regime's range) | Character |
|---|---|---|
| **Price stability** | `r̂* + π + 1.5 × (π − 2) + cycle_lean` | leans against inflation first; accepts slumps |
| **Growth** | `r̂* + π − 1.5 + 0.5 × max(0, π − 5) + cycle_lean/2` | runs warm; only reacts to inflation above 5%, or frenzy |
| **Peg defence** (gold only) | `world_rate + 0.5 × reserve_shortfall_pp` | keeps gold flows at zero; ignores the domestic cycle |

`r̂*` is the bank's **estimate** of the neutral rate: true value plus a slow random-walk
error of ±1.5pp (±0.5pp under CBI; shrinking with finance techs). `cycle_lean` is the
replacement for the deleted rate-hike button's AI logic: +2 frenzy, +1 boom, +1 if bubble
pressure ≥ 65, −2 recession, −3 panic. Before phase 2, `π` is 0 and mandates reduce to
`r̂* + cycle_lean` variants.

**Why CBI is not just "automation".** Delegation already gives everyone automation. CBI is
a *commitment device*: the player cannot override the bank, cannot monetise deficits, and
cannot pre-load a loose stance before a war. In exchange markets believe the mandate:
lower premium and floor, faster-anchoring expectations (disinflation is cheaper), and a
better estimate of r\*. A player planning to inflate away war debt should not want it.
Mandate changes under CBI take effect after a 12-month delay **(proposed)**.

**AI.** AI countries are always delegated. Mandate by rule: gold standard → peg defence;
at war, or `scaled_debt ≥ 0.5` → growth; otherwise price stability. This runs inside the
monthly update for `is_player = no` — a **documented exception** to
`mod_systems.md` "Do not move AI logic out of the buttons". Precedent:
`common/journal_entries/je_covert_warfare.txt:125-202`. That rule protects the discrete
toggle buttons, which all stay; here the mandate is a shared player/AI mechanic and no
`ai_chance` is bypassed. Avoid the orphan-gate trap recorded at
`scripting_best_practices.md:2953` — the AI branch must carry no gate the player branch lacks.

A national-bank country **without the JE** (no `stock_exchange` or no level-10 urban
center) has no dashboard and is auto-delegated to price stability.

---

## 7. Risk premium

`rate paid = policy rate + risk premium`. The premium is **one computed, floored number**
built from visible modifier contributions.

### 7.1 Modifier type

New script-only type in `common/modifier_type_definitions/banking_cycle_modifier_types.txt`:

```
country_risk_premium_add = { color = bad percent = yes decimals = 1 script_only = yes game_data = { ai_value = 0 } }
```

Vanilla's scale (0.01 = 1pp) so there is one unit convention across the mod. Tooltips read
"Risk premium: +1.0%". Needs name + `_desc` loc in
`localization/english/te_modifiers_l_english.yml` (the engine gives no warning for missing
loc), and literals ≥ 0.0005 to pass `modifier_visibility_audit`.

```
te_risk_premium = max( floor , 100 × modifier:country_risk_premium_add + computed terms )
floor = 0.5   (0.25 under central bank independence)
```

JE-scope tool modifiers still feed the country-scope `modifier:` read — the same path
`banking_cycle_advance_variables` already uses for `country_finance_momentum_monthly_add`.

### 7.2 Capital-market access premium

Rate levels are **historically realistic throughout** (owner decision; weaker countries
getting cheaper debt than vanilla's 40% is accepted). What keeps Siam or Afghanistan out of
the London market is a permanent **access premium** that shrinks as a country builds
financial institutions. It replaces vanilla's five −2pp tech reductions and is
**front-loaded**, because Britain in 1836 (two of five techs) must land near Consols:

| Source | Premium (pp) |
|---|---|
| Base — no finance techs | +8.0 |
| `banking` | −4.0 |
| `central_banking` | −2.5 |
| `mutual_funds` | −0.5 |
| `international_exchange_standards` | −0.5 |
| `modern_financial_instruments` | −0.5 |
| No `stock_exchange` | +2.0 |

The surcharge keys on **`stock_exchange`, not on having the JE**: the JE's other gate (a
level-10 urban center) is not a capital-market signal.

*(The interview floated a flat −2pp per tech from a +10 base. That puts 1836 Britain near
9%, so the weights are front-loaded instead. Same idea, different curve.)*

### 7.3 Rank and recognition

A ×0.2 conversion of vanilla's rank mults gives a GP −10pp, which is meaningless against a
dial with a 0% floor. Designed table instead, carried on the rank `INJECT`s so it shows in
rank tooltips:

| Rank | Vanilla `_mult` | Premium (pp) |
|---|---|---|
| Great power | −0.50 | +0.5 |
| Major power | −0.25 | +1.0 |
| Minor power | — | +2.0 |
| Insignificant power | +0.25 | +3.0 |
| Unrecognized major | +0.50 | +4.0 |
| Unrecognized regional | +0.75 | +6.0 |
| Unrecognized | +1.00 | +8.0 |

### 7.4 Anchor table (sanity check, policy/world rate 4%)

| Case | Build-up | Pays | Vanilla today |
|---|---|---|---|
| Britain 1836 | 4 + premium (0.5 rank + 1.5 access − 1 gold − 0.6 bank = 0.4 → **floor 0.5**) | **4.5%** | ~8% |
| USA 1840 (no bank) | 4 + 1 spread + 1 rank + 4 access | **10%** | ~13% |
| Siam 1850 | 4 + 1 spread + 6 rank + 8 access + 2 no exchange | **21%** | ~35% |
| Late-game GP, target 3% | 3 + 0.5 rank − 0.5 laissez-faire − 1.5 bank − 2 mod techs → floor 0.5 | **3.5%** | **~0.2%** |
| Same GP in a panic, after default | 3 + 0.5 + 2 phase + 10 bankruptcy | **15.5%** | ~0.4% |

### 7.5 Converting every existing source

**Rule for the mod's flat `_mult` modifiers: pp = mult × 20**, snapped to 0.1pp — the value
the mult had against vanilla's unranked 20% base. They switch to `country_risk_premium_add`.

| Group | Today (`_mult`) | Becomes (pp) |
|---|---|---|
| Phases: panic / downturn / stagnation | +0.10 / +0.05 / +0.02 | +2.0 / +1.0 / +0.4 |
| Tools: deposit guarantee / emergency liquidity / FX support / FX devaluation / coop credit expansion | −0.01 / −0.04 / −0.01 / +0.02 / −0.03 | −0.2 / −0.8 / −0.2 / +0.4 / −0.6 |
| Tools: **rate hike / OMO** | +0.05 / −0.04 | **interest field deleted** (the dial replaces it; OMO → QE, §11) |
| Crash interventions (6) | +0.02 … −0.06 | +0.4 … −1.2 |
| Banking event outcomes (14) | −0.10 … +0.20 | −2.0 … +4.0 |
| Great Depression / bystander | +0.15 / +0.05 | +3.0 / +1.0 |
| Crisis capital controls / monetary stabilisation | +0.05 / +0.08 | +1.0 / +1.6 |
| `colonial_military_garrison_modifier` | +0.05 | +1.0 |
| **Hand-judged:** `declared_bankruptcy` | +0.50 | **+10.0** |
| **Hand-judged:** `institution_national_bank` | −0.05 / level | **−0.3 / level** (×20 would be −5pp at level 5) |

The mod's existing `_add` users re-type to the premium so the floor covers them:
`treasury_strain_persistence_modifier` (+0.5), `neocolonial_dependency_imposed_modifier`
(+1.0), `finreg_interest_rate_hike` (+1.0 — a law-stall event modifier, unrelated to the
deleted button despite the name), the two Shell sources (−1.0 → −0.3). The mod's five techs
(`era_6.txt:172`, `era_8.txt:93`, `era_9.txt:561`, `era_10.txt:300`, `era_12.txt:376`)
drop from −2pp to **−0.4pp each** — at realistic levels −2pp is a third of the whole rate.

**Vanilla, cancelled at source** with inverse `INJECT`s that carry the new premium in the
same block (precedent: `common/laws/sol_expectations_vanilla_injections.txt:9-23`, shipped
since April): six country ranks, `law_laissez_faire` (−0.25 → −0.5pp), five finance techs.
This is the owner's "convert the big multipliers" decision.

**Vanilla, deliberately left alone** (owner: widen only if balance demands): IG traits
(−0.075…−0.15), amendments (mult −0.1/−0.2; add +0.01…+0.05), companies, character trait,
event modifiers. Consequence to document in the tooltip: these still *multiply* the whole
stack, so a −20% amendment is −20% of (policy + premium).

**Generator trap.** `scripts/generators/gen_banking_events.py:2085-2155` embeds six
`country_loan_interest_rate_mult` modifiers and appends them to `extra_modifiers.txt`. It is
a one-shot script (not in `docs/auto_generated_files.md`). Update its strings or mark it
do-not-rerun.

### 7.6 Computed premium terms **(proposed)**

- **Debt load:** 0 below `scaled_debt` 0.25, rising linearly to +4pp at 1.0. Realistic,
  automatic, and makes the cheap-debt world self-limiting. Check first whether the engine's
  unscriptable per-loan bucket already does this (VERIFY IN-GAME).
- **Monetisation:** +0.5pp per level (§11).
- **Unanchored expectations (P2):** +0.25pp per pp that |expected inflation − 2| exceeds 3.

---

## 8. Stimulus channel and the hidden neutral rate

```
real_rate   = policy_rate − inflation                  (inflation = 0 before phase 2)
stance_gap  = clamp( real_rate − neutral_rate , −10 , +10 )
```

A JE-scope modifier `banking_monetary_stance` carries unit fields and is scaled by the gap
(clamped to ±4 for this purpose, so steady-state momentum stays inside the ±5 bar):

| Field | Per pp of **tight** gap | Calibration |
|---|---|---|
| `country_finance_momentum_monthly_add` | −0.125 | a 2pp tight stance = the old rate hike (−0.25) |
| `country_bubble_pressure_monthly_add` | −0.75 | 2pp ≈ −1.5 (old hike: −2.0; old OMO: +0.8) |
| `state_capitalists_investment_pool_contribution_add` | −0.01 | cheap money feeds the pool |

Loose gaps apply the same fields with the opposite sign.

**Who gets the stance modifier: only countries that set a policy rate** (national bank,
market or cooperative economy). For a bankless country the "policy rate" is world + spread
≈ 5 against a neutral near 3 — applying the channel would leave every
`law_no_national_bank` country permanently 2pp tight, a hidden penalty nobody chose. A
market rate clears at neutral by definition, so bankless, commodity-money, crypto and
command-economy countries get **stance gap = 0** and no modifier. What they give up is the
*ability to lean against the cycle*, not a standing drag. (Exception, phase 3: a
gold-standard country forced above neutral to defend the peg does feel it — that is the
cost of the peg.)

The hike's
`interest_group_ig_industrialists_approval_add = -2` moves to §13.

**Neutral rate (proposed — the first tuning target).** It is the load-bearing hidden
number; a per-era constant would be learnable in one campaign and make "hidden" hollow.

```
neutral_rate = clamp( era_base + growth_term + walk , 1 , 6 )
  era_base    3.0 (eras 1–4) → 2.5 (5–8) → 2.0 (9–12)
  growth_term 0.25 × (trailing GDP growth % − 2), clamped ±1.5
              — yearly: store last year's gdp in a var, compare
  walk        mean-reverting random walk, ±0.1 per month, reusing the cycle's
              random_list nudge machinery (banking_cycle_effects.txt:1670-1723)
```

The stance **band** shown to the player, and the mandate formulas, use
`neutral_rate + estimation_error`, never the true value.

---

## 9. Inflation (phase 2)

`te_inflation` is a signed annual %, clamped −10…100. `te_inflation_expected` is its
exponential moving average. Both exact on the dashboard.

### 9.1 Monthly update

```
Δπ per month =
    − 0.05 × stance_gap                      loose money
    + phase term                             frenzy +0.15 · boom +0.08 · expansion +0.03 · stable 0
                                             stagnation −0.03 · downturn −0.08 · panic −0.15
    + 0.02 if bubble_pressure ≥ 65
    + 0.03 × max(0, deficit % of GDP − 1)    ×2 at war
    + 0.25 × monetisation_level              §11
    + 0.10 if QE active                      §11
    + 100 × modifier:country_inflation_pressure_add / 12     wage pressure, §9.4
    + cost_push                              §9.3, clamped ±0.5
    + 0.10 × (expected − π)                  persistence: inflation gravitates to expectations
    + regime pull                            gold: 0.10 × (0 − π) · crypto: 0.10 × (−1 − π)

expected += α × (π − expected)     α = 1/24; 1/12 under CBI; gold/commodity pin expected to 0
```

Deficit % of GDP reuses the shape of `financial_cycle_government_fiscal_policy_effect_size`
(`common/script_values/extra_script_values.txt:1808`).

### 9.2 Bands and consequences

| Band | π | Consequences (one scaled static modifier per band; validate every name via `/modifier-search`) |
|---|---|---|
| Deflation | < −1 | momentum drag; Rural Folk + Trade Union anger (debtors); rate paid **rises** via §10 |
| Comfort | −1…3 | none; **real-wage dividend** active (§9.4) |
| Elevated | 3…8 | lower-strata cost-of-living squeeze (candidate: `country_sol_expectations_lower_offset_add`); Petite Bourgeoisie − |
| High | 8…20 | + `state_tax_waste_add` (collection lag); Landowners / Armed Forces − (fixed incomes); investment-pool efficiency − |
| Very high | 20…50 | all of the above, steeper; bubble pressure + (flight to real assets) |
| **Hyperinflation** | ≥ 50 | crisis state + event chain: currency reform (reset π and expected to 5; investment-pool wipe-out, radicals, +5pp premium for ten years) / dollarise (adopt no-policy regime) / ride it out |

### 9.3 Cost-push — the goods basket

Goods prices are real relative prices capped at 0–2× base, so a *level* is not inflation: a
world where oil is permanently dear is just a fact about that world. Only **changes** are
inflationary:

```
index     = Σ weight × (price / base − 1)      per market
cost_push = 0.3 × (index − basket_avg) × 100 , clamped ±0.5 pp/month
basket_avg += (1/36) × (index − basket_avg)
```

| Good | Weight | | Good | Weight |
|---|---|---|---|---|
| grain | .30 | | fish | .075 |
| clothes | .15 | | meat | .075 |
| coal | .15 | | wood | .05 |
| oil | .15 | | fabric | .05 |

A spike is an impulse; whether it *persists* depends on whether the central bank
accommodates it (through expectations) — the 1970s, and the source of the stagflation
dilemma: hike into a slump, or tolerate it and let expectations drift.

Implementation: reuse the shipped numeric price-ratio idiom `st_res_<good>_price_rel`
(`common/script_values/st_res_script_values.txt:1054-1078`; rationale
`strategic_reserve_system.md:204-212`). **Block form only** — that doc warns the dot-chain
form may silently read zero. Exclude `local = yes` goods. **Seed `basket_avg` to the first
observation** or month 1 produces a phantom shock; the clamp also absorbs the jump when a
country changes market. Performance option: compute once per market owner, members read
`market.owner.var:`. VERIFY IN-GAME: reading `mg:oil` in a market that has never traded oil
— gate that term on the tech if it errors.

### 9.4 Wage pressure and the real-wage dividend **(proposed)**

New *visible* script-only type `country_inflation_pressure_add` (annual pp, same scale and
registration as §7.1), placed on labour laws so the effect is never hidden:

| Law | Wage pressure (pp/yr) |
|---|---|
| `law_no_workers_rights`, `law_combination_acts`, `law_anti_strike_laws` | −0.2 |
| `law_regulatory_bodies`, `law_right_to_associate` | +0.2 |
| `law_worker_protections`, `law_corporatized_unions` | +0.4 |
| `law_factory_councils` | +0.5 |
| welfare: `law_wage_subsidies` +0.2 · `law_old_age_pension` +0.2 · `law_universal_basic_income` +0.5 | |

**Compensation**, so this is not a hidden tax on progressive laws: while inflation is in
the comfort band, each +0.1pp of wage pressure also yields a lower-strata loyalist trickle
and +0.01 `country_finance_momentum_monthly_add` (wage-led demand). Outside the band the
dividend switches off and above 8% the same laws add to persistence (wage-price spiral).
Strong labour laws become *better* under competent monetary management, not uniformly worse.

---

## 10. Debt: expected versus actual inflation

```
rate_paid_pts = policy_rate + risk_premium + expected_inflation − inflation     (floored 0.5)
```

Because all money is real, lenders demand compensation for the inflation they *expect*, and
the government's real burden falls by the inflation that *occurs*. Steady state: the terms
cancel and the country pays policy + premium. **Surprise** inflation erodes debt; then
expectations catch up and the country pays for it until it disinflates.

Worked example — fiat, no CBI, policy 3, premium 2, π = expected = 2 → pays 5%.
Monetise at level 3 for two years: π climbs to ~12 while expected lags at ~6 → pays
3 + 2 + 6 − 12 → **floored 0.5%**. Stop: expected peaks near 10 while π falls back to 4 →
pays 3 + 2 + 10 − 4 = **11%**, plus the unanchored-expectations premium, for several years.
Under CBI (α doubled) the hangover is half as long — but CBI forbade the monetisation.
That is the tradeoff: a cheap war now, expensive peace later.

---

## 11. Monetisation and QE (phase 2)

**Monetise the deficit** — a 0–3 stepper (same widget shape as the target). Requires fiat or
digital currency, a national bank, **not** CBI.

- Each level: `country_minting_add` worth 0.25% of annual GDP per year (scaled static
  modifier), +0.25pp/month inflation, +0.5pp premium.
- The real decision is war finance and the §10 "inflate it away" strategy.

**Open-market operations → QE.** `cb_open_market_ops` survives with its tech gate
(`country_can_use_open_market_ops_bool`, `era_6.txt:177`), law lock, 4 intervention points
and treasury cost. Changes:

- `possible`: the rate-hike exclusion (`banking_policy_triggers.txt:25`) becomes
  `var:te_policy_rate <= 0.01` — **usable only at the floor**.
- Effect: keeps momentum +0.35 and services +5%; bubble +0.8 → **+1.5**; adds inflation
  +0.10/month; the interest field is deleted.
- AI weights rewritten: use at the floor in recession or deflation.
- Under digital currency the floor is −3%, so QE arrives later — negative rates substitute.

`cb_policy_rate_hike` / `cb_disable_policy_rate_hike` are **deleted** (§18).

---

## 12. World rate, gold, and the peg (phase 3)

### 12.1 World rate

`global_var:te_world_rate` = GDP-weighted mean `te_policy_rate` of **great powers that have
a national bank**. Bankless GPs are excluded — their rate is derived from the world rate, so
including them is circular. Britain, France and Austria start with a national bank, so it is
defined from day one. Computed on the global `on_monthly_pulse` with two accumulator globals
(Σ gdp/10⁶ × rate, Σ gdp/10⁶ — the scaling is fixed-point headroom), seeded in
`te_init_global_state` (`common/on_actions/extra_on_actions.txt:22-31`). Fallback 4 when
`has_global_variable` is false. Before phase 3 the reference is the constant 4.

Effect: a small country is pulled around by the hegemon's central bank.

### 12.2 Gold flows

Gold-standard countries with a national bank only:

```
gap  = clamp( policy_rate − world_rate , −5 , +5 )
flow = gap × 0.004 × gdp          per month; positive = inflow
```

Applied with **`add_treasury`** from the monthly country update — **not** a scaled
`country_expenses_add`. The sign argument: an expense modifier feeds `total_expenses`,
which the mod's own fiscal-stimulus reader and the §9 deficit driver both read, so a gold
*outflow* would register as deficit spending — stimulus and inflation — the wrong sign
twice. It would also distort the AI's budgeting.

Sizing: the vanilla reserve limit is 0.2 × annual GDP, so 1pp of gap moves ~2% of the limit
per month and a 2pp gap empties full reserves in about two years. Inflows past the limit hit
the engine's diminishing returns, which caps hoarding (VERIFY IN-GAME for a one-off
`add_treasury`). Show the monthly flow on the dashboard — `add_treasury` never appears in
the budget ledger. A gold-standard country *without* a national bank pays the world rate, so
its gap and its drain are zero by construction.

### 12.3 Peg confidence and the convertibility crisis

When `scaled_gold_reserves < 0.1` or the country is in debt, stop the treasury flow (a
negative `add_treasury` would only deepen the debt) and move `te_peg_confidence` (0–100)
instead: −3 per pp of negative gap per month, −2 in panic/downturn, −2 if `scaled_debt ≥
0.5`; +2 per month when the gap is ≥ 0 and reserves are rebuilding.

At ≤ 20 the **convertibility crisis** event fires:

| Option | Effect |
|---|---|
| **Defend** | target forced to world + 4 for a year; peg confidence +40; downturn likely |
| **Suspend convertibility** | acts as fiat for 5 years (free dial, inflation-constrained) without the law change; gold credibility bonus lost for 10 years; premium +2pp |
| **Devalue the peg** | one-off gold reserve revaluation + export boost; confidence reset to 50; infamy and GP relations (the costs the old *Devalue* button carried); expected inflation +3 |

This absorbs banking event 12 ("Gold Standard Pressure") and the gold-peg-defence event at
`events/banking_cycle_events.txt:1510-1548`.

---

## 13. Creditor-versus-debtor politics

The banking event chain already runs on asset-vs-wage incidence
(`docs/audits/strata_social_axis_exceptions.md`). The standing stance gets the same
treatment — gently, and only when sustained (|gap| ≥ 1 for six months):

| Condition | Approve | Disapprove |
|---|---|---|
| Tight stance | Landowners, Petite Bourgeoisie (savers, rentiers) | Industrialists, Rural Folk (debtor farmers), Trade Unions |
| Loose stance | Industrialists, Rural Folk, Trade Unions | Landowners, Petite Bourgeoisie |
| Inflation ≥ 8% | — | Petite Bourgeoisie, Landowners, Armed Forces |
| Deflation | Landowners | Rural Folk, Trade Unions |

**Regime laws gain stances.** `lawgroup_monetary_policy` is the only economy law group with
`ideological_opinion_impact = 0`. Proposed direction: hard money (commodity, gold) endorsed
by Landowners and Petite Bourgeoisie, opposed by Rural Folk and Trade Unions (*Cross of
Gold*); fiat endorsed by Trade Unions, Rural Folk and Intelligentsia; CBI endorsed by
Industrialists and Petite Bourgeoisie. Stances go through the generator input
`ideology_modifications.py` — **never hand-edit `common/ideologies/modified.txt`**
(`docs/auto_generated_files.md`).

---

## 14. Alternative economies

Cooperative ownership runs the full system (§5.3); its existing
`cooperative_credit_expansion` interest field converts under §7.5. Command economy keeps its
`ce_*` plan tools unchanged, pays administered rate + premium, and is excluded from the
world rate, gold flows and inflation until repressed inflation is designed.
`te_banking_law_change_cleanup` (`common/on_actions/extra_on_actions.txt:34-61`) must clear
delegation and monetisation on entering command economy, **without removing any variable
that backs a multiplier**.

---

## 15. Exchange rates — sketch only (phase 4)

Organising idea: the **policy trilemma** — pick two of a fixed exchange rate, free capital
flows, an independent rate.

| Corner | In the mod | Result |
|---|---|---|
| Peg + open capital | gold standard (§12) | rate must track the world rate |
| Float + open capital | fiat / digital | free rate; the **exchange rate is an outcome** of the rate gap and the inflation gap. Weak = export edge + imported inflation; strong = the reverse |
| Peg + capital controls | gold or a declared peg, plus `cb_capital_controls_outflow` | independent rate *and* a peg, at an efficiency cost |

- `cb_fx_devaluation` and `cb_fx_support` **dissolve**: devaluing is the §12.3 crisis option
  under a peg, and an outcome of loose policy under a float. `cb_fx_swap_lines` and
  `cb_capital_controls_outflow` survive.
- The exchange rate is one more abstract index (`te_fx_index`, 100 = par) feeding
  `state_trade_advantage_mult`-style effects and the §9 cost-push term (imported inflation).
- **Capital controls carry a political cost (owner decision):** held **outside a crisis**
  (not panic/downturn, not at war, no peg crisis) they accrue an **escalating** approval
  penalty with **Industrialists** and the **Petite Bourgeoisie** — major if prolonged — a
  *mild* Trade Union bonus (labour broadly backed Bretton-Woods-era controls, so the choice
  has a constituency), and an investment-pool efficiency drag. The counter resets when
  controls are lifted.

Open questions: a declared non-gold peg (to a hegemon's currency) as a law or a diplomatic
pact; whether `te_fx_index` is displayed exactly; currency-union interaction with customs
unions; whether swap lines should lend peg confidence.

---

## 16. Implementation mapping

### 16.1 Interest plumbing — country scope

Countries without the JE or a national bank must still pay world rate + premium, and
JE-scope `multiplier =` cannot read country properties (`scripting_best_practices.md:400`).
So the rate lives in **country scope**, refreshed for every country.

Two static modifiers, always added in the **same effect block**:

```
te_monetary_base_offset = { country_loan_interest_rate_add = -0.2 }
te_monetary_rate_paid   = { country_loan_interest_rate_add = 0.01 }   # multiplier = var:te_rate_paid_pts
```

Idiom: `sol_expectations_apply_strata_shifts`
(`common/scripted_effects/sol_expectations_effects.txt:143-160`). Invariant: the offset is
never present without the rate modifier, so Σ`_add` never sits at ≤ 0; a freshly spawned
country with neither pays vanilla's 20% until its first pulse — a safe fallback. Skip the
re-apply when the change since last month is under 0.05. `REPLACE` the
`country_loan_interest_rate_add` type definition to `decimals = 1` (precedent:
`common/modifier_type_definitions/mod_entity_modifier_types.txt:3486`).

**No `REPLACE` of any vanilla entity — cancel-`INJECT`s only.** Rejected alternatives:
`REPLACE:base_values` (must restate an engine-named block plus the mod's own 40-key
`INJECT:base_values`, re-diffed every patch; and any REPLACE silently drops every INJECT
into that entity); a back-solver over `modifier:country_loan_interest_rate_mult` (the
division blows up as 1 + Σmult → 0, which vanilla stacks can already reach).

**Do not gate the plumbing on `banking_system_enabled`.** The cancel-injects are file-level,
so with the rule off a passive pulse (constant reference rate + premium) must still run.

### 16.2 Single owner: the monthly country update

New on-action on `on_monthly_pulse_country` calling `te_monetary_monthly_update`. **No new
variable goes in `je_banking.txt`'s `immediate`** — that block resets unguarded
(`:119-133`) and the JE is `can_revolution_inherit`. Every variable initialises behind
`has_variable`, and **none is ever removed** (`modifier_multiplier_var_audit`).

Order: 0 init → 1 regime code → 2 target (mandate if delegated / AI / CBI / bank-without-JE,
else player's var; clamp to regime) → 3 drift → 4 bankless = world + spread → 5 premium →
6 *[P2]* basket → inflation → expected → 7 rate paid → 8 stance gap → 9 re-apply interest
modifiers → 10 *[P3]* gold flow / peg confidence.

| Variable | Range | Phase |
|---|---|---|
| `te_policy_rate_target` | regime range, integer | 1 |
| `te_policy_rate` | same, fractional | 1 |
| `te_mon_delegated` / `te_mon_mandate` | 0–1 / 1–3 | 1 |
| `te_risk_premium` | floor–40 | 1 |
| `te_rate_paid_pts` | 0.5–60 | 1 |
| `te_neutral_rate` / `te_neutral_error` | 1–6 / ±1.5 (hidden) | 1 |
| `te_mon_stance_gap` | −10–10 | 1 |
| `te_inflation` / `te_inflation_expected` | −10–100 | 2 |
| `te_basket_index` / `te_basket_avg` | −1–1 | 2 |
| `te_monetisation_level` | 0–3 | 2 |
| `te_peg_confidence` | 0–100 | 3 |
| `global_var:te_world_rate` | — | 3 |

**Arithmetic with `change_variable` only.** Drift: temp = target − actual; if temp > 0.34
add 0.3333, if < −0.34 subtract 0.3333, else set actual = target. Moving average: temp =
observation − average; multiply by a **literal** α; add `var:tmp`. Vary α with an if/else on
the law, never a computed operand — `change_variable`'s `divide =`/`multiply =` operands
resolve only literals and `var:` (`scripting_best_practices.md:431`).

### 16.3 Stance into the JE pulse

`banking_monetary_stance` is applied in JE scope, its multiplier fed through an
`owner = { add = … }` wrapper script value — the shipped pattern at
`common/script_values/cultural_hegemony_script_values.txt:94-102` — placed directly after
`banking_cycle_update_fiscal_policy` in `je_banking.txt`'s monthly pulse. It lands one
month late (modifier changes are invisible inside the same effect block, `:433-462`), as the
fiscal modifier already does. Design the consumer to be pulse-order independent.

### 16.4 UI

Target and monetisation steppers copy the Cultural Hegemony funding stepper: one
`op`-parameterised scripted GUI, `is_shown` scope-free, `is_valid`/`effect` branching on
`scope:op` (`common/scripted_guis/cultural_hegemony_sguis.txt:65+`,
`gui/journal_entry_widgets/cultural_hegemony_widget.gui:430-485`), step effect in
`hidden_effect` with one `custom_tooltip` outside it. All dashboard sguis keep
`ai_is_valid = { always = no }`. Guard every `var:` read (GUI gotcha #14). Add
`te_policy_rate`, `te_inflation` and rate-paid to the history store
(`common/scripted_effects/te_history_banking_effects.txt`) — the charts are also the
oscillation detector for §20 risk 5.

### 16.5 What must not change

`finance_cycle_value`, `finance_cycle_momentum`, `bubble_pressure` keep their names and
ranges: harvest conditions (`common/harvest_condition_types/extra_harvest_condition_types.txt:54-64`),
the construction market, ruler traits and the history charts read them directly.

---

## 17. Engine unknowns — VERIFY IN-GAME

**Phase-1 coding gate.** Checks 1–3 need **no new code** — read tooltips on the current
build. They decide whether cancel-`INJECT`s sum with vanilla's values or overwrite them. If
INJECT is last-wins, `+0.5` on `great_power` would **double** a GP's rate instead of
zeroing its mult.

1. A great power's budget-panel interest tooltip: does it still list rank −50% and
   laissez-faire −25%? If yes, separate `modifier = {}` blocks merge (the mod already
   INJECTs both).
2. The breakdown of `state_expected_sol_from_literacy`: the mod injects −5 against
   vanilla's +5 (`extra_modifiers.txt:17`). **0 ⇒ values sum; −5 ⇒ last wins.**
3. Does expected SoL under `law_industry_banned` net to zero (same key summing across blocks)?

Fallbacks if summing fails — techs: compensate in script (+pp per researched finance tech
inside `te_risk_premium`, no vanilla touch); ranks / laissez-faire: `REPLACE` in
`common/country_ranks/extra_country_ranks.txt` — owed regardless in that case, because the
mod's existing GP/major INJECTs would already be wiping vanilla's blocks.

Later checks:

4. `modifier:country_loan_interest_rate_add` / `_mult` readable in a script value? (The mod
   already reads other `base_values` keys this way; this pair is unverified. Used only for a
   debug readout.)
5. `[JournalEntry.GetCountry.GetYearlyInterestRate|1%]` in widget loc — the `GetPlayer.`
   form is proven, the `Country.` form is not.
6. Relative order of global `on_monthly_pulse`, `on_monthly_pulse_country` and the JE's pulse.
7. Does `add_modifier` accept a **negative** multiplier? (Base offset variant; digital currency.)
8. Does the engine's per-loan interest bucket already scale with debt? (§7.6.)
9. `mg:<good>` reads in a market that never traded the good (§9.3).
10. A one-off `add_treasury` above the gold reserve limit — diminishing returns? (§12.2.)
11. Is the existing fiscal-policy input live? `financial_cycle_government_fiscal_policy_effect_size`
    reads `total_expenses` / `income` / `gdp` bare but is applied as a **JE-scope** multiplier
    (`banking_cycle_effects.txt`, `banking_cycle_update_fiscal_policy`), which
    `scripting_best_practices.md:400` says evaluates to `'none'`. No error appeared in the
    2026-09-19 `debug.log`, so this is unconfirmed — check the modifier's value on the JE
    while running a deficit. Either way, **do not copy that shape**: §9.1's deficit term runs
    in country scope and caches to a variable.

---

## 18. Deletions and save migration

Deleting `cb_policy_rate_hike` / `cb_disable_policy_rate_hike` touches:

- `common/journal_entries/je_banking.txt:45-46`
- `common/scripted_buttons/timeline_extended_scripted_buttons.txt:9-54`, plus nine
  `ai_chance` cross-references to `banking_tool_rate_hike_active` (lines 79, 100, 394, 414,
  444, 464, 494, 543, 593) → new triggers `banking_stance_is_tight` / `_is_loose`
  (`var:te_mon_stance_gap >= 1` / `<= -1`)
- `common/scripted_effects/banking_policy_effects.txt:8-19`;
  `common/scripted_triggers/banking_policy_triggers.txt:11-17,25`;
  `common/scripted_triggers/market_triggers.txt:35`
- `common/scripted_guis/banking_dashboard_scripted_gui.txt:130,171-184`;
  `gui/journal_entry_widgets/banking_dashboard_widget.gui:288-301,899-912`
- `common/scripted_guis/te_history_scripted_gui.txt:43-50` (marker rows; old marker vars in
  saves are harmless orphans)
- `common/static_modifiers/extra_modifiers.txt:775-783`;
  `common/scripted_effects/extra_effects.txt:380`
- loc: `te_miscellaneous_l_english.yml:105-106,120-121,1215,1267,1293` (uppercase keys — a
  lowercase grep misses them; `grep -i policy_rate_hike`); `te_concepts_l_english.yml:351`
- `scripts/generators/add_tech_modifiers.py:257,285` hardcodes the OMO button name and loc
- docs: `mod_systems.md` banking section; examples at
  `scripting_best_practices.md:2199-2202,2355` go stale but break nothing

No `events/` file and no `test_*.py` references either tool.

**Save migration.** AI countries holding `banking_policy_rate_hike` would lose 2
intervention points with no button to switch it off. Keep the static modifier defined for
one release and add a one-shot `je:je_banking_cycle = { remove_modifier =
banking_policy_rate_hike }` to the monthly pulse. `legacy_modifier_cleanup.txt` is the home
for the eventual removal.

---

## 19. Phases

Each phase is playable alone. Later phases can be cut.

| Phase | Ships | Interim rule until the next phase | Exit criteria |
|---|---|---|---|
| **1** | country-scope plumbing; `country_risk_premium_add` + full §7.5 conversion + access/rank tables; target + drift; delegation + mandates (cycle-lean only); CBI binding; regime dial ranges; stance → cycle; rate-hike deletion; dashboard block; history series | reference rate = constant 4; gold standard target clamped to 4 ±2; inflation = 0; OMO usable at the floor but without its inflation cost | §17 checks 1–3 pass; anchor table (§7.4) reproduced in-game within 0.5pp; observer-mode run shows no country at the 0.5 floor or the 60 cap by accident; AI countries' stance tracks the cycle |
| **2** | inflation, expectations, basket, wage-pressure type + real-wage dividend, §10 formula, monetisation, QE costs, hyperinflation chain, §13 stance politics | gold standard still on the ±2 band | 50-year observer run: median fiat inflation 1–4%, no oscillation with period < 3 years, at least one organic hyperinflation and one deflation |
| **3** | world rate, gold flows, peg confidence, convertibility crisis; regime law stances | FX buttons unchanged | a GP rate hike visibly drains a small gold country; AI on peg defence survives a 2pp world-rate rise |
| **4** | FX index, trilemma, capital-controls politics; devalue/support deleted | — | — |

---

## 20. Risks

1. **Uncancelled `_add` sources drive the rate to ≤ 0 from day one** — five vanilla techs
   alone total −10pp. *Mitigation:* cancel or compensate (§17); clamp `te_rate_paid_pts`;
   keep the engine's own rate on the dashboard so a bad stack is visible immediately.
2. **Debt gets much cheaper worldwide** (unrecognized ~35–40% → ~20%; minor ~18% → ~8–10%),
   and the brakes that replace that cost arrive in phases 2–3. Owner accepted this.
   *Mitigation:* access + rank tables; the debt-load premium (§7.6); and as a fallback the
   **global** credit-limit defines (`COUNTRY_MIN_CREDIT_SCALED`) — blunt, all countries at
   once, but real.
3. **INJECT semantics unproven.** *Mitigation:* the phase-1 coding gate (§17), with a
   fallback per axis.
4. **Variable lifecycle** — unguarded `immediate` resets; a multiplier-backing var removed
   by a cleanup effect; a national-bank country with no JE and therefore no dial.
   *Mitigation:* single owner on the country pulse, guards everywhere, never remove,
   auto-delegate the JE-less.
5. **Feedback instability** — inflation → rate → cycle → inflation; a circular world rate;
   one-month lags between pulses. *Mitigation:* clamps on the stance gap and cost-push;
   seeded averages; bankless GPs excluded from the world rate; history charts of rate and
   inflation as the oscillation detector in observer runs.
6. **The neutral rate is learnable** if its random component is too small, making the
   hidden-information decision hollow. *Mitigation:* tune the walk first; keep the band
   driven by the estimate, not the truth.

---

## 21. Tuning constants

| Constant | Start | § |
|---|---|---|
| Drift per month | 1/3 pp (2/3 digital) | 4 |
| Target range: gold / fiat / digital | 0–15 / 0–25 / −3–25 | 5 |
| Bankless spread | 1.0 | 5 |
| Administered rate (command) | 3.0 | 5 |
| Rate-paid clamp | 0.5 – 60 | 4 |
| Premium floor (CBI) | 0.5 (0.25) | 7 |
| Gold / CBI credibility | −1.0 / −0.5 | 5 |
| `_mult` → pp conversion | × 20 | 7.5 |
| Access base / techs / no exchange | +8 / −4, −2.5, −0.5 ×3 / +2 | 7.2 |
| Rank table | 0.5 · 1 · 2 · 3 · 4 · 6 · 8 | 7.3 |
| Debt-load premium | 0 → +4 over `scaled_debt` 0.25 → 1.0 | 7.6 |
| Stance per pp: momentum / bubble / pool | 0.125 / 0.75 / 0.01; gap clamp ±4 | 8 |
| Neutral rate: era base / growth coeff / walk | 3 → 2 / 0.25 / ±0.1 | 8 |
| Estimation error (CBI) | ±1.5 (±0.5) | 6 |
| Mandate inflation weight / target | 1.5 / 2% | 6 |
| Inflation: stance coeff / persistence / regime pull | 0.05 / 0.10 / 0.10 | 9.1 |
| Expectation α (CBI) | 1/24 (1/12) | 9.1 |
| Basket: k / avg α / clamp | 0.3 / 1/36 / ±0.5 | 9.3 |
| Hyperinflation threshold | 50% | 9.2 |
| Monetisation per level: minting / inflation / premium | 0.25% GDP/yr / +0.25/mo / +0.5 | 11 |
| Gold flow per pp / gap clamp | 0.004 × GDP per month / ±5 | 12.2 |
| Peg crisis threshold | confidence ≤ 20 | 12.3 |
| Reference rate before phase 3 | 4.0 | 12.1 |

---

## 22. Appendix — known drift in the existing banking docs

Found while researching this design; **not** fixed here (tracked in #328; the
`/modifier-grants` coverage gap that forced a manual file walk for §7.5 is #327):
`journal_entry_systems.md` and `mod_systems.md` disagree with `je_banking.txt` on widget
slot numbers; the banking-law table in `mod_systems.md` omits `law_state_owned_banking` and
carries stale values; the documented 12-month event cooldown is 18 in script; event counts
are out of date (82 blocks); `banking_points_max_from_law` is written monthly and read by
nothing; a comment in `banking_cycle_effects.txt` says the Great Depression needs 20% of
world GDP where `great_depression_gdp_threshold` is 50%.
