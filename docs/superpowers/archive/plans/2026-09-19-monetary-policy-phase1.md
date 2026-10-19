# Plan: Monetary Policy — Phase 1

**Spec (binding authority):** `docs/systems/monetary_policy_design.md` — §19 row 1 is the
shipping list. Each task names the spec sections that hold its exact values; read those
sections (not the whole spec) plus §2 and §4 for orientation. Section line ranges:
§3 74-100 · §4 103-146 · §5 149-217 · §6 220-261 · §7 264-420 · §8 423-481 ·
§14 879-888 · §16 920-1031 · §17 1034-1100 · §18 1103-1134 · §21 1183-1222.

**Branch:** `feat/monetary-policy-phase1`, in the main checkout (the mod state server and
all reload audits only see this tree).

**Out of scope (phases 2–4):** inflation, basket, wage pressure, monetisation, QE costs,
world rate, gold flows, peg confidence, FX, IG stance politics (§13), regime law stances.
Phase-1 interim rules (§19 row 1): reference/world rate = `era_base`; gold-standard target
clamped to `era_base` ±2; inflation = expected inflation = 0; OMO usable only at the floor,
without an inflation cost.

## Global Constraints

- Tabs + UTF-8 BOM on every touched brace-based `.txt` / `.gui`; run
  `python3 scripts/format_paradox_tabs.py <files>` on edited `.txt` (never on generator-owned
  files, YAML, JSON, Python). Loc files: BOM + `l_english:` header; add keys to existing
  `*_l_english.yml`, then `python3 organize_loc.py` (add a `startswith` rule for any new
  prefix whose base key has 4+ tokens).
- Never hand-edit auto-generated files (`docs/auto_generated_files.md`); edit generator input.
- Every new variable initialises behind `has_variable`; **never** `remove_variable` on any
  of them; **no new variable in `je_banking.txt` `immediate`**.
- `change_variable` / `set_variable` op slots take a literal, `var:X`, or a **named script
  value** — never a bare trigger read (`gdp`, `scaled_debt`). No inline block arithmetic
  inside `multiplier = { }`.
- `te_monetary_base_offset` and `te_monetary_rate_paid` are always added in the **same
  effect block**; the offset is never present without the rate modifier.
- Do **not** gate the interest plumbing on `banking_system_enabled`.
- No `REPLACE` of any vanilla database entity (ranks, laws, techs, static modifiers). The one
  permitted `REPLACE` is the `country_loan_interest_rate_add` *modifier type definition*.
- The engine silently ignores unknown modifier names: validate every modifier key via
  `curl 'http://localhost:8950/modifier-search?q=<name>'`. Every new static modifier,
  modifier type, scripted button/gui text, and concept needs loc (engine gives no warning).
- Modifier literals ≥ 0.0005. `*_modifier_time` values are days. `any_*` triggers take no `limit`.
- Hidden state (`te_neutral_rate`, `te_neutral_error`, `te_mon_stance_gap`, momentum, bubble)
  is **never printed** in any tooltip, loc string or visible modifier (§8 "The rule").
- `finance_cycle_value`, `finance_cycle_momentum`, `bubble_pressure` keep names and ranges (§16.5).
- Verification for every task: `curl -s -X POST 'http://localhost:8950/reload?mod_only=true&audits_only=true'`
  and report the `warnings` and `parse_failures` arrays verbatim (new findings vs. baseline);
  plus `ruff check .` and the relevant `test_*.py` if Python changed. Do **not** run the full
  `unittest discover`. Do not commit `te_harbor_traits.txt` or regeneration churn unrelated to the task.
- Commit on `feat/monetary-policy-phase1` with a truthful `Co-Authored-By` (your own model). Do not push.
- Unit convention: variables are in **pp** (3.5 = 3.5%); modifier fields use vanilla scale
  (0.01 = 1pp), read back as `100 × modifier:X`.

## Pre-flight rulings (orchestrator)

- R1 — §17 checks 1–4 (INJECT sum vs last-wins) are unresolved. Techs: **script
  compensation** per R3 (no vanilla tech INJECT) — the spec calls this
  right regardless. Ranks + `law_laissez_faire`: **cancel-INJECTs** (spec's chosen path,
  same precedent as `sol_expectations_vanilla_injections.txt`). Isolate them in one file,
  `common/country_ranks/te_monetary_rank_injections.txt` / one clearly-marked law block, so a
  last-wins result is a one-file fix.
- R2 — `(proposed)` items: implement neutral-rate formula (§8), debt-load premium (§7.6),
  state-owned-banking row (§5.2, premium part only: +0.5 structural, no CBI bonuses). Defer:
  CBI 12-month mandate delay, §5.1 minting axis, France commodity-money dial.
- R3 — Vanilla tech compensation: the five vanilla finance techs still grant −2pp each
  engine-side via `_add`. Compensate **outside the premium tiers** (so the structural floor
  is unaffected): script value `te_mon_vanilla_tech_offset` = 2.0 × (researched vanilla
  finance techs), and step 9 writes the modifier with multiplier
  `te_rate_paid_applied = te_rate_paid_pts + te_mon_vanilla_tech_offset`. The access premium
  uses the §7.2 table values as-is. Displayed numbers use `te_rate_paid_pts`.
- **R3 superseded by owner decision (2026-09-19, PR #335) — tech cancel-INJECTs.** The five techs are cancelled engine-side in `common/technology/technologies/te_monetary_tech_injections.txt`; `te_mon_vanilla_tech_offset` and the `on_acquired_technology` hook are deleted. See `docs/systems/monetary_policy_design.md` §0.1 R3.

## Task 1: Registrations and the interface contract

Spec: §7.1, §16.1, §16.2 variable table, §8 (band modifiers, neutral-rate constants), §21.

Create (names below are the contract for Tasks 2–6 — use them verbatim):

1. Modifier types in `common/modifier_type_definitions/banking_cycle_modifier_types.txt`:
   `country_credit_standing_add`, `country_risk_premium_add` exactly as §7.1; `REPLACE` of
   the `country_loan_interest_rate_add` type def to `decimals = 1` (copy vanilla's other
   fields; precedent `mod_entity_modifier_types.txt:3486`). Loc (name + `_desc`) in
   `te_modifiers_l_english.yml`.
2. Static modifiers in `common/static_modifiers/extra_modifiers.txt`: `te_monetary_base_offset`,
   `te_monetary_rate_paid` (§16.1); five JE-scope `banking_stance_band_1`…`_5`
   (1 very loose … 5 very tight) carrying `state_capitalists_investment_pool_contribution_add`
   +0.04 / +0.02 / (neutral: a registered no-op or omit the field) / −0.02 / −0.04 (§8 table;
   validate the key). Loc for all.
3. Script values in a new `common/script_values/te_monetary_script_values.txt`:
   `te_mon_era_base` (3.0 eras 1–4, 2.5 eras 5–8, 2.0 eras 9–12 — find how the mod detects
   the current era and reuse it), `te_mon_scaled_debt_premium` (§7.6 debt load),
   `te_mon_access_premium` (§7.2 table), `te_mon_vanilla_tech_offset` (ruling R3), and any cached-read helpers Task 2 needs.
4. Scripted triggers in a new `common/scripted_triggers/te_monetary_triggers.txt`:
   `te_mon_has_dial` (national bank AND gold/fiat/digital AND NOT command economy),
   `te_mon_is_cbi`, `te_mon_is_command`, `te_mon_is_state_banking`,
   `banking_stance_is_tight` (`var:te_mon_stance_gap >= 1`, guarded) / `banking_stance_is_loose` (`<= -1`).
5. Variable names (document them in the header comment of the script-values file, with ranges
   from §16.2): `te_policy_rate_target`, `te_policy_rate`, `te_mon_delegated`, `te_mon_mandate`
   (1 price stability, 2 growth, 3 peg defence), `te_premium_structural`, `te_premium_cyclical`,
   `te_rate_paid_pts`, `te_rate_paid_applied` (last value written to the modifier),
   `te_neutral_rate`, `te_neutral_error`, `te_neutral_walk`, `te_mon_gdp_last_year`,
   `te_mon_stance_gap`, `te_mon_stance_band` (1–5), `te_mon_regime` (0 none/bankless, 1 commodity,
   2 gold, 3 fiat, 4 digital, 5 crypto, 6 command).

Nothing is wired yet. Verify with reload; `loc_coverage_audit` and `modifier_visibility_audit` must be clean for the new keys.

## Task 2: `te_monetary_monthly_update` — the single owner

Spec: §4, §5, §6, §7 intro + §7.6, §8, §14, §16.1, §16.2. Uses Task 1's names verbatim.

New `common/scripted_effects/te_monetary_effects.txt` with `te_monetary_monthly_update`
(country scope), order per §16.2 steps 0,1,2,3,4,5,7,8,9 (6 and 10 are later phases):

- 0 init behind `has_variable` (target/rate seeded to `te_mon_era_base`; neutral = era_base).
- 1 regime code → `te_mon_regime`.
- 2 target: mandate formula when delegated / AI / CBI / national bank without `je_banking_cycle`
  (auto price stability); else the player's var. Phase-1 formulas (§6, π terms **and the −2**
  dropped): price stability `r̂* + cycle_lean`; growth `r̂* − 1.0 + cycle_lean/2`; peg defence
  = `te_mon_era_base`. `r̂* = te_neutral_rate + te_neutral_error`. `cycle_lean` per §6 reads
  the JE's phase/bubble state — find how other country-scope code reads the banking JE's
  variables. Round to integer, hysteresis 0.75, clamp to regime range (§5.1; gold = era_base ±2).
  AI mandate rule per §6; the AI branch carries no gate the player branch lacks.
- 3 drift 1/3 pp per month (2/3 digital) using the §16.2 arithmetic.
- 4 no-dial: `te_policy_rate` = era_base + 1.0 (bankless / commodity / crypto); command = 3.0.
- 5 premium: structural = max(floor, 100 × `modifier:country_credit_standing_add` + access
  script value + state-banking +0.5) with floor 0.5 (0.25 CBI); cyclical = 100 ×
  `modifier:country_risk_premium_add` + debt-load script value.
- 7 `te_rate_paid_pts` = clamp(policy + structural + cyclical, 0.5, 60). A negative policy
  rate never lowers it below the floor (§4).
- 8 neutral rate (§8 formula: yearly growth term from cached gdp, ±0.1 monthly mean-reverting
  walk, estimation error random walk ±1.5 / ±0.5 CBI); `te_mon_stance_gap` = clamp(policy −
  neutral, ±10), **0 for no-dial countries**; `te_mon_stance_band` from gap + error
  (thresholds: ≤ −2 very loose, ≤ −0.75 loose, < 0.75 neutral, < 2 tight, else very tight).
- 9 re-apply both interest modifiers in one block when |pts − applied| ≥ 0.05 or the
  modifier is missing.

Wire: new on-action file hooking `on_monthly_pulse_country`, `on_game_started` (every
country), and the country-creation on-actions (find what vanilla fires for released /
civil-war / formed tags). Not gated on `banking_system_enabled`. Extend
`te_banking_law_change_cleanup` (§14): entering command economy sets `te_mon_delegated = 0`
without removing any variable.

Add a debug event in the style of `events/te_debug_un_events.txt` that prints every
`te_*` monetary variable for the player country (debug-only; hidden state is allowed there).

## Task 3: Convert every interest-rate source (§7.2–7.5)

Spec: §7.2, §7.3, §7.5, rulings R1 and R3.

First write `git grep -n country_loan_interest_rate -- common events` to a file and check it
against `curl localhost:8950/modifier-grants/country_loan_interest_rate_mult` (and `_add`);
the report must account for **every** mod line (converted / deleted / deliberately left, with reason).

- Mod `_mult` sites → `country_risk_premium_add` at pp = mult × 20 snapped to 0.1pp
  (field value = pp × 0.01), per the §7.5 table; hand-judged rows as given;
  `institution_national_bank` → `country_credit_standing_add` −0.003/level.
- Rate-hike / OMO interest fields: deleted (the rest of the rate-hike removal is Task 4).
- Mod `_add` users re-typed per §7.5 (cyclical vs structural as listed; mod techs −0.4pp ×4, −0.2pp era 12; Shell −0.3).
- Rank table (§7.3) as `country_credit_standing_add` on rank INJECTs, together with the
  cancel of vanilla's `_mult` (R1) — in one isolated file. Decentralized +10: find where a
  decentralized-only modifier can live; else compute it in `te_mon_access_premium` and say so.
- `law_laissez_faire`: cancel −0.25 mult, add −0.5pp structural.
- Vanilla finance techs: no INJECT; handled by R3 in script (confirm Task 1's script value does this).
- `scripts/generators/gen_banking_events.py:2085-2155`: update the embedded strings and add a do-not-rerun banner.
- Vanilla sources listed as "deliberately left alone" stay untouched.

Report the §7.4 anchor table recomputed by hand from the shipped values.

## Task 4: Delete the rate-hike tool (§18)

Spec: §18 in full (the touch list is exact; re-verify line numbers by grep,
`grep -ri policy_rate_hike`). Replace the nine `ai_chance` references with
`banking_stance_is_tight` / `banking_stance_is_loose` (Task 1) choosing the sense that
preserves each weight's intent. Save migration: keep the `banking_policy_rate_hike` static
modifier defined, add the one-shot JE-scope removal, note the eventual removal in
`legacy_modifier_cleanup.txt`. Update `scripts/generators/add_tech_modifiers.py` only where it names the deleted button.

## Task 5: Stance into the cycle; OMO at the floor

Spec: §8, §11 (OMO bullets — phase-1 subset only), §16.3.

- In `banking_cycle_advance_variables`: momentum −0.125 × gap and bubble −0.75 × gap per
  month, gap clamped ±4, via named script values reading the owner country's
  `te_mon_stance_gap` (guarded; tolerate a one-month-old value).
- Swap the `banking_stance_band_*` JE modifier when `te_mon_stance_band` differs from a
  stored `te_mon_stance_band_applied` (decide from variables, never `has_modifier` in the same block).
- Momentum tooltip gains a "Policy stance: [band]" line (custom loc), no number.
- `cb_open_market_ops` `possible`: replace the rate-hike exclusion with
  `var:te_policy_rate <= 0.01` on the country (guarded); delete its interest field if Task 3
  has not; rewrite AI weights: use at the floor in recession. Bubble +0.8 → +1.5. No inflation term.
- The rate hike's `interest_group_ig_industrialists_approval_add = -2` is dropped (moves to phase 2 §13); note it.

## Task 6: Dashboard block, steppers, history

Spec: §3 (phase-1 rows only), §16.4. Read `docs/guides/gui_modding_guide.md` gotchas first.

- New Monetary Policy block at the top of the dashboard's Monetary Policy category in
  `gui/journal_entry_widgets/banking_dashboard_widget.gui`: policy rate (1 decimal), target
  with −/+ stepper, rate the government pays (`JournalEntry.GetCountry.GetYearlyInterestRate`
  — unverified form, §17 check 6: also show `te_rate_paid_pts` beside it so a failure is
  visible), credit standing and risk premium with breakdown tooltips
  (`GetValueWithBreakdownFor` idiom used elsewhere in the mod) plus the computed terms listed
  in loc, stance **band** via customizable localization, delegation toggle + mandate selector.
- One `op`-parameterised scripted GUI for the target stepper, copying
  `common/scripted_guis/cultural_hegemony_sguis.txt:65+`; disabled with an explanatory tooltip
  when no dial / CBI / delegated / command. Delegation toggle and mandate selector sguis
  (peg defence only on gold). All with `ai_is_valid = { always = no }`; guard every `var:` read.
- No-dial countries see the block read-only with a one-line explanation of why.
- History: add `te_policy_rate` and `te_rate_paid_pts` series to
  `common/scripted_effects/te_history_banking_effects.txt` and the chart UI, following the existing series pattern.
- All loc explanatory (name the causal mechanism), `#b X#!` markup, never `[b]`.

## Task 7: Docs fold-in

- `docs/systems/mod_systems.md` § Banking Cycle and `docs/systems/journal_entry_systems.md`
  (**CRLF — preserve line endings; confirm with `file`**): fold in what shipped, remove the rate-hike tool.
- `docs/guides/vanilla_patch_runbook.md`: the −0.2 base-rate line (§16.1 last bullet) plus the
  rank mults, laissez-faire and tech values the mod mirrors.
- `docs/guides/scripting_best_practices.md`: fix the stale rate-hike examples (§18); record any engine lesson learned in Tasks 1–6 (read their reports in the workspace).
- Spec status banner: phase 1 implemented pending in-game §17 checks; list rulings R1–R3 as deviations.
- `docs/auto_generated_files.md` untouched unless a generator changed ownership.
