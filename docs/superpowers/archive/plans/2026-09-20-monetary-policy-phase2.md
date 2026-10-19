# Plan: Monetary Policy — Phase 2

**Spec (binding authority):** `docs/systems/monetary_policy_design.md` — §19 row 2 is the
shipping list; **§0 binds over §1–22 wherever they disagree** (it records what phase 1
actually shipped). Each task names the spec sections that hold its exact values; read those
sections (not the whole spec) plus §0.1, §2 and §4 for orientation. Section line ranges:
§0 24-246 · §3 305-331 · §4 334-377 · §5 380-448 · §6 451-492 · §7.6 642-651 · §8 654-712 ·
§9.1 721-799 · §9.2 801-813 · §9.3 815-850 · §9.4 852-876 · §10 880-944 · §11 947-993 ·
§13 1087-1107 · §14 1110-1118 · §16 1175-1304 · §17 1307-1388 · §19 1432-1443 · §21 1479-1517.

**What exists (phase 1):** read `docs/systems/mod_systems.md` § Banking Cycle →
**Monetary Policy (phase 1)** (file inventory, single-owner rule, ROOT-resolved multiplier
rule, hidden-state rule) and the **variable contract** in the header of
`common/script_values/te_monetary_script_values.txt` before touching anything.

**Branch:** `feat/monetary-policy-phase2`, in the main checkout (the mod state server and
all reload audits only see this tree).

**Out of scope (phases 3–5):** real world rate, gold flows, hot money, peg confidence,
convertibility crisis, regime-law *gold-supply* term, FX, capital-controls politics,
international arrangements. Phase-2 interim rules (§19 row 2): world/reference rate stays
`era_base`; gold-standard target stays on the reference ±2 band.

## Global Constraints

- Tabs + UTF-8 BOM on every touched or created brace-based `.txt` / `.gui` (check the BOM on
  **every** changed file: `head -c3 <file> | xxd`); run
  `python3 scripts/format_paradox_tabs.py <files>` on edited `.txt` (never on generator-owned
  files, YAML, JSON, Python). Loc files: BOM + `l_english:` header; add keys to existing
  `*_l_english.yml`, then `python3 organize_loc.py` (add a `startswith` rule for any new
  prefix whose base key has 4+ tokens). Loc markup is `#b X#!`, never `[b]`. Tooltip loc is
  explanatory: name the causal mechanism in plain language.
- Never hand-edit auto-generated files (`docs/auto_generated_files.md`); edit generator input.
- Appending to a Paradox file: anchor on the **outer** entity-closing brace.
- Every new variable initialises behind `has_variable` in `te_monetary_init_variables`;
  **never** `remove_variable` on any of them; **no new variable in `je_banking.txt`
  `immediate`**. Every new variable is added to the variable contract in the header of
  `te_monetary_script_values.txt` (name, range, hidden or shown).
- `change_variable` / `set_variable` op slots take a literal, `var:X`, or a **named script
  value** — never a bare trigger read (`gdp`, `scaled_debt`). No inline block arithmetic
  inside `multiplier = { }`.
- **Single owner:** `te_monetary_monthly_update` stays the only writer of the rate stack and
  now of every inflation variable. It is not idempotent; it is called only from
  `common/on_actions/te_monetary_on_actions.txt` (sole exception: the console-only debug
  events). Buttons, sguis and events write *inputs* and let the next pulse pick them up.
- **`add_modifier { multiplier = var:X }` resolves against ROOT.** Any new scaled country
  modifier is applied only inside the monthly update (whose ROOT is the country), following
  step 9's pattern, with a persistent `_applied` variable backing the multiplier.
- **Hidden state is never printed** in any tooltip, loc string, visible modifier or chart:
  `te_neutral_rate`, `te_neutral_error`, `te_neutral_walk`, `te_mon_stance_gap`,
  momentum, **`bubble_pressure` to a decimal** (§0.1), and — new in phase 2 —
  `te_inflation_core`, `te_inflation_noise` and the total inflation-pressure sum (ruling P7).
  Shown exactly: headline inflation, expected inflation, rate paid, the target, the
  monetisation level, and `country_inflation_pressure_add` / `country_wage_pressure_add` (what the player *chose*).
  `banking_stance_is_tight` / `_loose` stay `ai_chance`-only. The console debug events are
  the one place hidden state may be printed.
- §0.1 bindings that reach phase 2: OMO is fiat/digital only and floor-gated (digital floor
  −3); `era_base` everywhere in §9–§10 means the **world** value
  (`global_var:te_mon_era_base_world`, cached per pulse as `te_mon_era_base_now`), never a
  per-country one; the stance band is `gap − error`; regime rules are declarative modifiers
  granted on the law where a rule *is* a property of the law.
- Do **not** gate the plumbing on `banking_system_enabled`. With the rule off, inflation still
  runs (it feeds the rate every country pays); only JE-dependent inputs (cycle phase, bubble,
  tools) read as absent.
- No `REPLACE` of any vanilla database entity. Vanilla laws are extended with `INJECT:` in a
  new isolated file per concern.
- The engine silently ignores unknown modifier names: validate every modifier key via
  `curl 'http://localhost:8950/modifier-search?q=<name>'`. Every new static modifier,
  modifier type, scripted button/gui text, event and concept needs loc.
- Modifier literals ≥ 0.0005. `*_modifier_time` values are days. `any_*` triggers take no `limit`.
- `finance_cycle_value`, `finance_cycle_momentum`, `bubble_pressure` keep names and ranges (§16.5).
- Unit convention: variables are in **pp** (3.5 = 3.5%); modifier fields use vanilla scale
  (0.01 = 1pp), read back as `100 × modifier:X`.
- Every tuning constant from §21 is a **named script value** (or a clearly commented literal
  in exactly one place), so retuning is a one-line edit.
- Each task that adds variables extends the console printout in
  `events/te_debug_monetary_events.txt` with them.
- Verification for every task: `curl -s -X POST 'http://localhost:8950/reload?mod_only=true&audits_only=true'`
  and report the `warnings` and `parse_failures` arrays verbatim, new vs. baseline. **Baseline
  (2026-09-20, branch start): one warning — `loc_coverage_audit` `unreviewed: 1`; no parse
  failures.** Plus `ruff check .` and the relevant `test_*.py` if Python changed. Do **not**
  run the full `unittest discover`, and do not run a full (non-`audits_only`) reload unless the
  task says so — it rewrites vanilla-derived files to the older local vanilla clone; never
  commit that churn. Stage by path; never `git commit -a`; never commit `te_harbor_traits.txt`.
- Commit on `feat/monetary-policy-phase2` with a truthful `Co-Authored-By` (your own model). Do not push.
- `docs/systems/journal_entry_systems.md` and `docs/guides/gui_modding_guide.md` are **CRLF**
  — preserve line endings; confirm with `file <path>`.

## Pre-flight rulings (orchestrator)

- **P1 — `(proposed)` items in phase-2 scope: implement** §9.4 (wage pressure + real-wage
  dividend), the §9.1 credibility anchor table incl. state-owned banking c = 0.15, §7.6
  unanchored-expectations and monetisation premium terms. They are all named in §19 row 2 or
  load-bearing for the §10 tuning invariant.
- **P2 — still deferred:** §9.1 gold-supply term (the spec calls it a phase-3 companion; the
  plain regime pull `−π_core` carries the metallic deflation bias meanwhile), §5.1 minting
  axis (owner decision pending), CBI 12-month mandate delay, France's commodity dial,
  estimation error shrinking with techs.
- **P3 — monetisation is the GDP-scaled `country_minting_add`** (§11 marks it chosen).
- **P4 — deficit units.** §9.1 / §17 check 12 is unverified. Build the deficit term with one
  named script value `te_mon_deficit_annualise_factor` = **52** (the spec's reading: budget
  flows are weekly, `gdp` annual) and print the computed deficit-%-of-GDP in the debug event so
  the owner can flip it to 1 in one line. "Exclude minting from income": no trigger reads
  minting, so add back the *known* monetisation amount (level × 1% GDP/yr) to the deficit.
- **P5 — step order.** Step 6 (inflation) runs between 5 and 7 and reads **last month's**
  `te_mon_stance_gap` (step 8 runs after it; §16.3 already tolerates a one-month-old gap).
  Step 8's real rate becomes `te_policy_rate − te_inflation`.
- **P6 — who has inflation.** Every country except command economy (§14: excluded, π and
  expected held at 0). Bankless / commodity / crypto countries run it, because §4 makes them
  pay `era_base + own expected inflation + 1`. Their stance gap stays 0.
- **P7 — hidden-state leak in §9.1 (spec inconsistency, ruled).** Headline and expected are
  displayed exactly while `pressure` carries `−0.4 × stance_gap` with no random term — the
  same inversion §0.1 found for `bubble_pressure`. Ruling: add a hidden mean-reverting random
  walk `te_inflation_noise` (±0.1pp a month, bounded ±0.75pp, same `random_list` machinery as
  `te_neutral_walk`) to `pressure`; never display core, noise, or the pressure *sum*. The
  dashboard may show only the player-chosen `country_inflation_pressure_add` breakdown.
  Cost if wrong: one term to delete.
- **P8 — §13 "sustained stance" keys on the *displayed band*** (band ≤ 2 / ≥ 4 for six
  consecutive months), not the true gap: an IG modifier appearing exactly when `|gap| ≥ 1`
  would print a bit of r\*.
- **P9 — dollarisation** (§9.2 hyperinflation option) is a persistent flag variable
  `te_mon_dollarised` that makes `te_mon_has_dial` false (derived rate, gap 0), applies the
  −0.75 minting modifier and the metallic regime pull; it clears when the country next
  enacts a different `lawgroup_monetary_policy` law. The spec names no exit; this is the
  smallest one.
- **P11 — wage pressure gets its own type.** §9.4 puts wage pressure on
  `country_inflation_pressure_add`, which §11 also uses for event modifiers — so the real-wage
  dividend could not tell a labour law from a devaluation. Two types:
  `country_wage_pressure_add` (labour/welfare laws; feeds the dividend) and
  `country_inflation_pressure_add` (everything else). Step 6 sums both.
- **P10 — phase 1 is still pending in-game verification** (§0.3 items 2–5, 8–14 open). Phase 2
  does not block on it and inherits those checks.

## Task 1: Registrations and the interface contract

Spec: §9.1 (variables, constants), §9.2, §9.4, §11, §16.2 variable table, §21. Rulings P1–P9.

Create (names are the contract for Tasks 2–9 — use them verbatim). **Nothing is wired yet.**

1. Modifier types `country_inflation_pressure_add` and `country_wage_pressure_add` (P11) in
   `common/modifier_type_definitions/banking_cycle_modifier_types.txt`, same shape as §7.1's
   types (`color = bad percent = yes decimals = 1 script_only = yes`, `ai_value = 0`). Name +
   `_desc` loc in `te_modifiers_l_english.yml`.
2. Static modifiers in `common/static_modifiers/extra_modifiers.txt` (loc for all):
   - six country-scope inflation-band modifiers `te_inflation_band_deflation`, `_comfort`
     (empty — like `banking_stance_band_3`), `_elevated`, `_high`, `_very_high`, `_hyper`,
     carrying the §9.2 consequences. §9.2 gives directions and three exact numbers
     (`country_minting_mult` −0.3 / −0.8; `country_sol_expectations_lower_offset_add` and
     `state_tax_waste_add` as candidates): **validate every key**, size the rest so each band
     is strictly worse than the one before and *High* clearly outweighs the ~1.5pp rate-paid
     saving §10 computes for never disinflating (they are the deterrent). IG approval keys per
     §9.2 / §13's inflation rows. List every chosen value in the report as a table.
   - `te_monetisation_minting` = `{ country_minting_add = 1 }` (scaled; multiplier backed by
     `te_monetisation_minting_applied`).
   - `te_mon_dollarised_modifier` = `{ country_minting_mult = -0.75 }`.
   - `te_mon_real_wage_dividend` — unit modifier scaled per +0.1pp of wage pressure:
     `country_finance_momentum_monthly_add = 0.03` plus a small lower-strata loyalist trickle
     (validate the key; if no suitable country-scope key exists, say so and leave momentum only).
3. Variables (init in `te_monetary_init_variables`, documented in the contract header):
   `te_inflation` (headline, −10…100), `te_inflation_core` (hidden), `te_inflation_expected`,
   `te_inflation_noise` (hidden, ±0.75), `te_cost_push` (±6), `te_basket_index`,
   `te_basket_avg`, `te_basket_seeded` (0/1), `te_basket_market_owner` (scope var — for the
   re-seed on market change; or an equivalent the implementer justifies),
   `te_inflation_band` (1–6) / `te_inflation_band_applied`, `te_monetisation_level` (0–3),
   `te_monetisation_minting_applied`, `te_mon_dollarised` (0/1), `te_market_yield`,
   `te_mon_deficit_pct` (debug/readout cache), `te_mon_stance_months` (signed counter, P8),
   `te_mon_wage_dividend_applied`. All seeded to 0 (expected and core 0; `te_inflation_band` 2).
4. Script values in `te_monetary_script_values.txt`: every §21 phase-2 constant as a named
   value (`te_mon_core_speed` 0.10, `te_mon_stance_pressure_coeff` 0.4, the seven phase terms,
   `te_mon_bubble_pressure_term` 0.2, `te_mon_deficit_coeff` 0.3,
   `te_mon_deficit_annualise_factor` 52, `te_mon_monetisation_pressure` 2.5,
   `te_mon_qe_pressure` 1.0, basket k 0.3 / α 1/36 / clamp 6, de-anchoring span 10,
   unanchored premium 0.25 per pp beyond 3, monetisation premium 0.5, the hyperinflation
   threshold 50, band edges −1 / 3 / 8 / 20 / 50), plus `te_mon_expectation_alpha` and
   `te_mon_credibility_c` implementing the §9.1 table (state-owned 0.15, manual 0.25, delegated
   0.4, CBI 0.7 at α 1/12, gold/commodity pinned) and `te_mon_inflation_anchor` (2; 0 metallic).
5. Triggers in `te_monetary_triggers.txt`: `te_mon_has_inflation` (P6),
   `te_mon_is_metallic` (gold or commodity money), `te_mon_can_monetise` (fiat or digital,
   national bank, not CBI, not command, not dollarised). Extend `te_mon_has_dial` with
   `NOT = { var:te_mon_dollarised = 1 }` (guarded).

Verify with reload; `loc_coverage_audit` and `modifier_visibility_audit` clean for the new keys.

## Task 2: Step 6 — the inflation engine

Spec: §9.1, §9.3, §14, §16.2 (order, `change_variable` arithmetic). Rulings P4–P7, P9.

New step `te_monetary_update_inflation` in `te_monetary_effects.txt`, called between steps 5
and 7, skipped (π, core, expected, cost-push held at 0) when `te_mon_has_inflation = no`:

- **Basket (§9.3).** `index = Σ weight × (price/base − 1)` over the eight goods, using the
  shipped block-form idiom of `st_res_<good>_price_rel`
  (`common/script_values/st_res_script_values.txt`; rationale in
  `docs/systems/strategic_reserve_system.md`) — **block form only**. Gate each good so a
  market that never traded it contributes 0 rather than erroring (find the mod's existing
  guard for this; if none, gate oil on its tech). Compute **once per market owner** where
  practical and have members read the owner's variable, tolerating a one-month-old value; if
  that proves unsafe, compute per country and say why. Seed `te_basket_avg` to the first
  observation (`te_basket_seeded`); **re-seed when the country's market owner changes**.
  `cost_push = 0.3 × (index − avg) × 100`, clamped ±6; then `avg += (1/36)(index − avg)`.
- **Pressure** exactly as the §9.1 block, every term a level in pp: stance (last month's gap,
  clamped ±4, 0 for no-dial), cycle phase (0 without the JE — reuse how `te_mon_cycle_lean`
  reads the JE), bubble ≥ 65, deficit (P4; ×2 at war), monetisation level, QE active
  (`banking_open_market_ops` on the JE), `100 × modifier:country_inflation_pressure_add`
  **plus** `100 × modifier:country_wage_pressure_add` (P11; nothing grants it until Task 6),
  the noise walk (P7), regime pull (metallic or dollarised: `−π_core`; crypto:
  `−(π_core + 1)`). **Omit** the gold-flow and gold-supply terms (phase 3 / P2).
- `π_core += 0.10 × (expected + pressure − π_core)`; `headline = core + cost_push`, clamped
  −10…100; expectations per §9.1 with `c_eff = c × max(0, 1 − |headline − anchor| / 10)`
  (metallic exempt: expected pinned to 0).
- `te_inflation_band` from headline (edges −1 / 3 / 8 / 20 / 50). Swapping the band modifier
  is Task 5.

Extend debug event `.1` to print every new variable plus the pressure terms individually
(console-only, so hidden state is allowed there). Report: a hand-traced 3-month example
(fiat, loose gap 2, boom) showing core moving as §9.1 predicts.

## Task 3: The rate stack with inflation — §10, §7.6, §6, §8

Spec: §4, §6 (full formulas), §7.6, §8 (real rate), §10. Rulings P5, P6.

- Step 4 (no-dial): `te_policy_rate = era_base + te_inflation_expected + 1.0`; command stays 3.0.
- Step 2 mandates regain their π terms — the **full** §6 formulas with π = `te_inflation_core`
  (mandates look through cost-push): price stability `r̂* + π + 1.0 × (π − 2) + cycle_lean`;
  growth `r̂* + π − 1.0 + 0.5 × max(0, π − 4) + cycle_lean/2`; peg defence unchanged
  (`era_base`). Growth must never come out more hawkish than price stability. Update the
  file-header "PHASE 1 HAS NO INFLATION" note.
- Step 5 cyclical premium gains: monetisation +0.5pp × `te_monetisation_level`; unanchored
  expectations +0.25pp per pp that `|expected − 2|` exceeds 3.
- Step 7: `te_market_yield = max(te_policy_rate, era_base + te_inflation_expected)`;
  `te_rate_paid_pts = clamp(market_yield + structural + cyclical − te_inflation, 0.5, 60)`.
  The existing rule "a negative policy rate never lowers rate paid below the floor" holds.
- Step 8: `real_rate = te_policy_rate − te_inflation`; gap and band from it.
- Dashboard/tooltip loc that explains the rate-paid build-up (phase 1's breakdown text) gains
  the lenders'-floor and inflation lines. No hidden state printed.

Report: reproduce §10's first worked line (π = expected = 2, policy 5, premium 2 → 5%) by
hand from the shipped formulas, and the gold-vs-fiat steady-state parity claim.

## Task 4: Monetisation, QE costs, and the existing minting content — §11

Spec: §11, §14, §9.1 (the two pressure terms already read these inputs). Ruling P3.

- `te_monetisation_level` 0–3 with step-down / step-up effects beside the phase-1
  `te_mon_effect_*` controls, valid only under `te_mon_can_monetise`. The effects write the
  level only.
- In the monthly update (ROOT-safe), re-apply `te_monetisation_minting` with
  `te_monetisation_minting_applied` = level × (1% of annual GDP expressed in the units
  `country_minting_add` uses — §11 says weekly minting; derive from `gdp`, show the unit
  reasoning in the report), following step 9's remove / re-add / skip-if-unchanged pattern.
  Remove it when the level is 0 or `te_mon_can_monetise` fails — **and force the level to 0**
  then (CBI enacted, law changed, command economy; §14 via `te_banking_law_change_cleanup`
  without removing any variable).
- `banking_open_market_ops`: nothing new in its modifier (the +1.0pp QE pressure is read by
  step 6 from the tool being active); rewrite its `ai_chance` to §11's "at the floor in
  recession **or deflation**" (add a deflation weight reading `te_inflation`, guarded), and
  make its tooltip state the inflation cost. Close phase 1's known gap: remove an active
  `banking_open_market_ops` when the country leaves fiat/digital.
- AI monetisation: §6 keeps AI always delegated but says nothing on AI monetisation. Give the
  monthly update a small AI rule: level 1 when at war **and** `scaled_debt ≥ 0.5`, level 2
  when additionally `in_default` or `weeks_until_bankruptcy` is short; otherwise step back to
  0; never under CBI. The player branch carries no gate the AI branch lacks beyond choice.
- Reconcile `monpol_currency_stability` / `monpol_currency_devaluation` (six uses in
  `events/extra_law_events.txt`): add a `country_inflation_pressure_add` field to each
  (stability negative, devaluation positive, 0.5–1.0pp; justify), and gate event #40
  *Hyperinflation Panic* on `te_inflation ≥ 20` (guarded) or retitle it — say which and why.

## Task 5: Inflation bands and the hyperinflation chain — §9.2

Spec: §9.2, §10 ("the path that must not pay"), ruling P9.

- Swap the `te_inflation_band_*` country modifier inside the monthly update when
  `te_inflation_band` ≠ `te_inflation_band_applied` (decide from variables, never
  `has_modifier` in the same block). Comfort is an applied empty modifier only if Task-1 loc
  renders sensibly; otherwise apply nothing in comfort and say so.
- New `events/te_inflation_events.txt` (+ loc, picture/icon from the available lists in
  `docs/guides/event_creation_guide.md` — read its boilerplate and Option Tradeoff
  Principles first): the **hyperinflation crisis** fires once when headline ≥ 50 (not again
  while a cooldown variable holds), three options per §9.2 — *currency reform* (π, core and
  expected reset to 5; investment-pool wipe-out; radicals; +5pp cyclical premium for ten
  years via a timed `country_risk_premium_add` modifier), *dollarise* (P9), *ride it out*
  (no reset; the band modifier keeps biting; re-offer after the cooldown). Options must be
  non-dominated with `ai_chance` tagged per option. Event writes inputs/variables directly
  only where the spec requires a reset (π / expected); it never calls the monthly update.
- Optional flavour if budget allows and only if cheap: one-shot notification events on first
  entering *High* and *Deflation*. Must be wired (no orphans — `orphaned_event_audit`).
- Add the dollarisation exit to the law-change hook (P9).

## Task 6: Wage pressure and the real-wage dividend — §9.4

Spec: §9.4. Ruling P1.

- New `common/laws/te_monetary_wage_pressure_injections.txt`: `INJECT:` a
  `modifier = { country_wage_pressure_add = … }` into each law in the §9.4 table
  (values ×0.01). Check each law key exists via the server (`/laws` or entity lookup); for a
  mod-owned law, edit it in place instead of injecting. Skip and report any key that does not
  exist.
- Dividend: in the monthly update, while `te_inflation_band` is comfort, apply
  `te_mon_real_wage_dividend` scaled by `max(0, 100 × modifier:country_wage_pressure_add) × 10`
  (i.e. per +0.1pp) — positive pressure only; remove it outside the band. ROOT-safe scaled
  pattern with `te_mon_wage_dividend_applied`.
- "Above 8% the same laws add to persistence": in step 6, when headline ≥ 8, add positive
  wage pressure a second time (document as the wage-price spiral).
- Law tooltips must make the tradeoff legible: the modifier `_desc` explains pressure *and*
  the comfort-band dividend.

## Task 7: Creditor-versus-debtor politics — §13

Spec: §13, ruling P8, `docs/auto_generated_files.md` (ideologies are generator-owned).

- `te_mon_stance_months`: +1 per month in band ≥ 4 (reset to 0 when crossing), −1 per month
  in band ≤ 2, decays to 0 in band 3; at ≥ 6 / ≤ −6 apply `te_mon_stance_politics_tight` /
  `_loose` (country static modifiers with the §13 IG approval rows; validate
  `interest_group_ig_*_approval_add` keys; magnitudes gentle, ±1 — the deleted rate hike
  carried −2 on Industrialists). Swap by variable, not `has_modifier`. Only for countries with
  a dial. The inflation ≥ 8% and deflation rows ride on Task 1's band modifiers — confirm
  they are there and not double-counted.
- Regime law stances: `lawgroup_monetary_policy` has `ideological_opinion_impact = 0`.
  Implement §13's direction through the generator input `ideology_modifications.py` (read how
  it expresses a law-group stance; run the generator explicitly — an `audits_only` reload skips
  regenerators — and commit only the files that generator owns). If stances on this law group
  need a new *ideology* rather than edits to IG-leader ideologies, stop at the smallest
  faithful version and report what was left.

## Task 8: Dashboard and history

Spec: §3 (phase-2 rows), §16.4. Read `docs/guides/gui_modding_guide.md` gotchas first (**CRLF**).

- Monetary Policy block: **Inflation** and **Expected inflation** rows (exact, 1 decimal) with
  tooltips explaining what each feeds (real rate / rate paid; lenders' floor / mandates); an
  **inflation band** name via customizable loc with what the band costs; a **Chosen pressure**
  rows showing `country_inflation_pressure_add` and `country_wage_pressure_add`, each with
  `GetValueWithBreakdownFor`; the **Monetise the deficit** 0–3 stepper (new ops on
  `banking_mon_control_sgui`, same shape as the target stepper; disabled with one
  cause-specific line when `te_mon_can_monetise` fails). Never core, noise, the pressure sum,
  or anything in the hidden list. No-dial and command countries: readouts only.
- History: add a `te_inflation` series to
  `common/scripted_effects/te_history_banking_effects.txt` and a chart in
  `banking_history_widget.gui` following the policy-rate pair precedent (inflation is signed —
  use the signed-axis variant). Tooltips print exact figures.
- All sguis keep `ai_is_valid = { always = no }`; guard every `var:` read.

## Task 9: Debug harness — §19 row 2 exit criteria

Spec: §9.1 ("debug harness"), §10 worked example, §19 row 2.

Extend `events/te_debug_monetary_events.txt` (console-only, `# REVIEWED` orphan suppression
as the existing four):

- **Pin**: make the player a fiat national-bank country with a fixed manual target (enact the
  laws via effect, delegation off, set target) — and unpin.
- **Fast-forward**: run `te_monetary_monthly_update` N times (12 and 60) for ROOT, the
  sanctioned exception to the single-owner rule; note that the JE cycle does not advance with it.
- **Scenario**: set monetisation level 3 + target 5 (the §10 war case) in one event.
- **Readout**: one event printing the rate build-up (market yield, premiums, inflation,
  expected, rate paid), all hidden state, every pressure term, `te_mon_deficit_pct` (P4).
- Header comment: the exact console sequence that reproduces §10's worked example and the
  never-disinflate invariant check, with the expected numbers.

## Task 10: Docs fold-in

- Spec: STATUS banner → phase 2 implemented pending in-game verification; new **§0.4 "Phase 2
  as shipped"** with rulings P1–P10 plus every deviation recorded in Tasks 1–9's reports
  (read them in the workspace), the deferred list, and a phase-2 **in-game checklist** (deficit
  units P4 / §17 check 12; `mg:` read in a market that never traded the good, §17 check 10;
  §19 row 2's observer-run and harness criteria; hidden-state sweep incl. P7).
- `docs/systems/mod_systems.md` § Banking Cycle: a **Monetary Policy (phase 2)** subsection —
  files, step 6, the new hidden-state members, the scaled-modifier sites, monetisation, bands,
  politics. `docs/systems/journal_entry_systems.md` (**CRLF**): dashboard rows.
- `docs/guides/scripting_best_practices.md`: any engine lesson from Tasks 1–9.
- `docs/auto_generated_files.md` only if a generator's ownership changed.
