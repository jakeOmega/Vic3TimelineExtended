# Monetary Policy — Design

> **STATUS: PHASES 1–6 IMPLEMENTED, PENDING IN-GAME VERIFICATION.** Phase 6 (§19 rows 6a / 6b /
> 6c — the swap line as a repayable capped single-provider loan, the guarantee's call counter,
> `non_fulfillment` on the friendly three, treaty leverage, and the two hostile articles
> `imposed_currency_peg` and `debt_receivership`) was reviewed (§15B), planned and ruled
> (§15C, §15C.5) and built on 2026-09-21, all in one day; see
> [§0.10](#010-phase-6-as-shipped--rulings-deviations-and-open-checks) for what shipped, the
> thirteen deviations from the plan, and the three new engine checks (§17 checks 22–24) it
> leaves open. The whole of it can be
> switched off at game setup while the Banking Cycle stays: `banking_system_rule` gained a third
> setting, `banking_system_simplified`, on 2026-09-21 — see
> [§0.9](#09-the-banking_system_simplified-game-rule--2026-09-21), which also carries the owner's
> ruling on what the rate does under it and the one trigger (`te_mon_full_system`) the whole gate
> hangs on. Phase 5 (§19 rows 5a /
> 5b / 5c — the anchored state, the `currency_peg` / `swap_line` / `lender_of_last_resort`
> treaty articles, the power-bloc common currency, subject currency boards, the
> `cb_fx_swap_lines` deletion) was implemented on 2026-09-21; see
> [§0.8](#08-phase-5-as-shipped--rulings-deviations-and-open-checks). Phase 4 (§19 row 4 —
> the exchange-rate index, world inflation, the trade edge, imported inflation, capital
> controls as the trilemma's third corner, the FX-tool deletion) and the narrow commodity
> dial were implemented on 2026-09-21; see
> [§0.7](#07-phase-4-as-shipped--rulings-deviations-and-open-checks) and §0.6. Phase 3 (§19 row 3 — the
> real world rate, gold flows and hot money, peg confidence, the convertibility crisis)
> shipped on `feat/monetary-policy-phase3` on 2026-09-20; see
> [§0.5](#05-phase-3-as-shipped--rulings-deviations-and-open-checks). Phase 2
> (§19 row 2 — inflation, monetisation and QE costs, the §9.2 bands and hyperinflation
> chain, wage pressure, §13 stance politics) shipped on `feat/monetary-policy-phase2` on
> 2026-09-20 and has not been seen in a running game either; see
> [§0.4](#04-phase-2-as-shipped--rulings-deviations-and-open-checks). **Phases 4 and 5 were
> scoped on 2026-09-20** ([§15](#15-exchange-rates-and-the-trilemma-phase-4),
> [§15A](#15a-international-monetary-arrangements-phase-5)), written against phase 3 **as
> shipped** (§0.5), not against §12 as first drafted. Written 2026-09-19 from a design
> interview with the mod owner plus an engine-feasibility pass, then revised the same day
> after two independent reviews on PR #329 (one with a monthly simulation of §9–§10). Every number is a starting
> point for tuning, collected in [§21](#21-tuning-constants). Items marked **(proposed)**
> were not explicitly decided by the owner. Items marked **VERIFY IN-GAME** cannot be
> proven from files.
>
> **Read [§0](#0-phase-1-as-shipped--deviations-and-open-checks) before anything else if you
> are touching the implementation**: what phases 1, 2 and 3 actually shipped (§0.1–§0.3,
> [§0.4](#04-phase-2-as-shipped--rulings-deviations-and-open-checks) and
> [§0.5](#05-phase-3-as-shipped--rulings-deviations-and-open-checks) respectively), where
> they deviate from the design sections below, what was deferred, and the in-game
> verification checklist — one list, numbered 1–14 for phase 1, 15–35 for phase 2 and 36–47
> for phase 3.
> Sections 1–22 remain the *design*, not a description of the code — where they disagree with
> §0, §0 is what shipped. The implemented parts are folded into `mod_systems.md` § Banking
> Cycle → **Monetary Policy (phase 1)** and **(phase 2)**, and `journal_entry_systems.md`
> § Banking Cycle (plus **(phase 3)**); this file stays the spec for the remaining phases.

This extends the Banking Cycle (`je_banking_cycle` — see `mod_systems.md` § Banking Cycle
and `journal_entry_systems.md`). Read those first.

---

## 0. Phase 1 as shipped — deviations and open checks

Phase 1 (§19 row 1) was implemented on `feat/monetary-policy-phase1` over seven tasks on
2026-09-19. **Nothing below has been seen in a running game.** Every claim in this section is
verified against the files; every claim about *behaviour* is not.

File inventory and the architectural rules (variable contract, single owner, hidden state,
the cancel-INJECT assumption, the migration window): `mod_systems.md` § Banking Cycle →
**Monetary Policy (phase 1)**. This section carries only what the design sections below get
wrong or leave open. **Phase 2 has its own equivalent in [§0.4](#04-phase-2-as-shipped--rulings-deviations-and-open-checks)**
— its rulings, its deferred list, its roughnesses and its half of the checklist (items
15–35) all live there; §0.1–§0.3 are phase 1's and are not rewritten.

### 0.1 Rulings — deviations from, or bindings on, the sections below

| # | Ruling | Why | Cost if wrong |
|---|---|---|---|
| **R1** | Vanilla **techs**, **ranks** and `law_laissez_faire` all use cancel-INJECTs, isolated one file each (`te_monetary_tech_injections.txt`, `te_monetary_rank_injections.txt`, `te_monetary_law_injections.txt`) | the owner confirms tech INJECTs sum in this mod (see R3); ranks and laissez-faire rode the same assumption and were read in game too — all three sum (§17 checks 1–4, answered 2026-09-19/20) | if INJECT is last-wins, the rates are wrong until each file becomes a `REPLACE:` — one file each |
| **R2** | Implemented: the §8 neutral-rate formula, the §7.6 debt-load premium, and §5.2's state-owned-banking **premium only** (+0.5 structural, no CBI bonuses). Deferred: §0.2 | the owner had not decided the `(proposed)` items | rework of small terms |
| **R3** | **Vanilla finance techs: cancel-INJECT.** Owner decision 2026-09-19 (PR #335), overriding the plan's script-compensation fallback. Each of the five takes `INJECT:<tech> = { modifier = { country_loan_interest_rate_add = 0.02 } }` in `common/technology/technologies/te_monetary_tech_injections.txt`; `te_mon_vanilla_tech_offset` and the `on_acquired_technology` hook that served it are **deleted**, and `te_rate_paid_applied` now equals `te_rate_paid_pts` | a tech tooltip promising "−2% interest" the mod silently takes back elsewhere is misleading; the owner reports tech INJECTs sum in this mod, so the `country_minting_mult = 0.1` in the same vanilla block survives | if INJECT is last-wins, the five techs make borrowing 2pp **dearer** and lose their minting bonus — visible on the tech tooltip, and a one-file `REPLACE:` fix |
| | **`te_mon_era_base` is a WORLD quantity**, not per-country: 3.0, −0.5 once any great power holds `macroeconomics`, −0.5 again for `globalization` | the spec calls this the world / reference rate in §7.4, §12.1 and §21, and **no era trigger or era detector exists** (see `scripting_best_practices.md` § "There Is No 'Current Era' Trigger") | five-line swap inside `te_mon_era_base` to per-country techs |
| | The stance band is computed from `gap − error`, not `gap + error` | §8 binds: the band and the mandates both use `neutral + error` as r̂\*, so the estimated gap is `policy − (neutral + error)`. Statistically identical, coherent with the mandates | one character |
| | §5.3's cooperative-ownership **−0.5pp on the neutral rate is implemented** | the spec's term binds over a task brief that omitted it | — |
| | `law_gold_standard` carries `country_credit_standing_add = -0.01` and `law_central_bank_independence` `-0.005` (§5.1/§5.2 credibility, §21) | phase-1 structural terms the implementation plan had omitted | without them Britain 1836 pays 5.0% |
| | **Britain 1836 lands at 4.0%, not §7.4's 3.5%** | §7.4 assumes `institution_national_bank` at level 2; GBR actually starts at level 0, so the −0.6 institution term arrives only once it invests. Inside the 0.5pp exit tolerance, and it converges on 3.5% over the first years | — |
| | The two hidden random walks are drawn **only** for countries with a dial | ~1,330 of ~1,400 `random_list` draws a month were pure waste — a no-dial country's gap is forced to 0 anyway | a no-dial country's hidden state *freezes* rather than decaying, and resumes from a stale walk if it later enacts a national bank |
| | OMO's floor under **digital currency is −3**, not 0 (`te_mon_policy_rate_at_floor`: `<= -2.99` under `law_digital_currency`, `<= 0.01` otherwise) | §11's prose ("QE arrives later") is the intent; its literal `0.01` formula was written for fiat | digital gets QE at 0 like fiat — one-line revert |
| | **OMO is fiat/digital only — owner decision 2026-09-20.** Binds over §11's `possible` bullet, which states the floor test and no regime test: `banking_possible_cb_open_market_ops` also requires `country_can_create_unbacked_money_bool`, a declarative bool granted by `law_fiat_currency` and `law_digital_currency` only. The floor test is wrapped in a `trigger_if` on that bool, so exactly one cause is reported per case (`banking_omo_unbacked_money_tt` off-regime, `banking_omo_rate_floor_tt` on it). The digital −3 ruling above **stands**, and `te_mon_floor_threshold` lost its `max = 0`: that clamp existed only to keep a gold band floor from counting as the floor, and gold can no longer reach the value | §5.1's ladder already says commodity money and crypto have "no QE" and gold's crisis tool is suspending convertibility (§12.3). Creating money to buy bonds is what a convertibility promise forbids. Gold was excluded only *accidentally*, by a `max = 0` and a 1pp band floor, and would have gained OMO for free the moment the reference rate reached 2.0 | a gold standard runs QE without giving up convertibility — the regime ladder's central tradeoff stops biting. One `custom_tooltip` and one law modifier to revert |
| | The dashboard's rate-paid row uses **`GetPlayer.GetYearlyInterestRate`**, not §17 check 6's `JournalEntry.GetCountry.…` form | `GetPlayer.` is the only form vanilla ships; the panel only ever renders for its owner, so both roots name the same country | **§17 check 6 stays untested** — a later phase needing the figure where `GetPlayer` is wrong must test the chain then |
| | `banking_policy_rate_hike`'s loc keys are **kept** while the modifier stays defined | §18's deletion list and its save-migration paragraph conflict; every defined modifier needs loc | they come out with the modifier next release (checklist in `legacy_modifier_cleanup.txt`) |
| | §7.5 says "Banking event outcomes (14)"; there are **13** | enumerated from the files; the stated −0.10…+0.20 range matches exactly, so it is a spec miscount, not a missed site | corrected in §7.5 |
| | **No step of the update has a second entry point**, as §16.2's ordering implies. An earlier phase-1 revision ran step 9 alone from `on_acquired_technology`; R3's cancel-INJECTs removed the reason for it and the hook is gone | the hook existed only to stop a vanilla finance tech's −2pp landing a month before the script compensation for it. The engine now cancels in the same instant | a second entry point reintroduced without a reason of the same kind risks the non-idempotent steps being called the same way |
| | **`bubble_pressure` must never be printed to a decimal on any surface** | §8 argues the cycle's random monthly nudges mask the stance term — true for momentum and cycle value, which `banking_cycle_advance_variables`' `random_list` nudges, but **bubble has no random term**. `banking_display_bubble_monthly_add` is exactly `modifier:country_bubble_pressure_monthly_add`, so Δbubble minus it is the stance push alone: `−0.75 × te_mon_stance_gap_clamped`, which inverts to the gap (and so to r\*) anywhere inside the ±4 clamp and off bubble's own 0/100 bounds — the whole stance-band range | the hidden-state rule (§8) fails through the banking panel, not through anything monetary |

### 0.2 Deferred (named in the design, deliberately not shipped)

- **CBI's 12-month mandate-change delay** (§6, `(proposed)`).
- **§5.1's minting axis.**
- **France's commodity-money dial** (§5.1).
- **Estimation error shrinking with finance techs** (§6) — the spec gives no magnitude. The
  error is a bounded walk at ±1.5pp (±0.5pp under CBI), re-bounded every month, so enacting
  independence narrows an already-wide error on the next pulse.
- Everything in §19 rows 2–4 (inflation, QE costs, world rate, gold flows, FX), plus the
  §13 stance politics the deleted rate hike's `interest_group_ig_industrialists_approval_add`
  was supposed to become.

Smaller known roughnesses, all judged acceptable for a first pass: the era proxy is
non-monotonic if a great power holds `globalization` without `macroeconomics`;
`te_mon_gdp_last_year` is seeded at game start, so the first year's growth term reads ≈ −0.3
once; `banking_stance_band_3` is an empty modifier (it had no icon until the phase-3 playtest, when it and `te_inflation_band_comfort` — by then also listed on the journal entry — were found logging an empty-texture error on every panel open; both carry one now) (the offset that used to read
"−20.0%" beside the rate it cancels is gone — the cancel moved into `INJECT:base_values`);
`pm_shell_pernis_refinery`'s structural term is `workforce_scaled`, so §7.5's "−0.3" is only
true at one building level; `cb_fx_support`'s `banking_stance_is_tight` easing weight may be
sign-wrong — moot once phase 4 deletes the button (§15.5), so not worth fixing before then; the band swap does not self-heal if a JE's
modifiers are lost while `te_mon_stance_band_applied` persists.

One entry on that list is now **stale and has been struck**: "OMO's `ai_chance` has no
recession-only term at the floor". Phase 2 rewrote those weights to §11's rule. Recession was
always covered — `banking_cycle_is_recession` is exactly the panic + downturn pair the
weights already scored separately — and the missing half, **deflation**, is now a `+40`
weight reading `var:te_inflation` against `te_mon_band_edge_deflation` (the §9.2 band edge,
not a literal 0, so the tool and the bands agree on what deflation is), with a symmetric
`−35` above the comfort band and a matching high-inflation weight on the *disable* side.

One asymmetry worth naming, because it looks like a bug and is not: the AI's **tools** are
better informed than the AI's **central bank**. `banking_stance_is_tight` reads
`te_mon_stance_gap`, the true gap against r\*, while a delegated bank's mandate steers on the
estimate r̂\* = `neutral + error`. Nothing leaks — `ai_chance` is never rendered — and the
alternative (a second, estimate-based stance trigger) buys a realism point nobody can observe.
Phase 3's stance politics should revisit it when IGs start reacting to the stance.

### 0.3 IN-GAME VERIFICATION CHECKLIST

One list, ordered by **how much breaks if the check fails**. Items 1–2 can invalidate the
whole premium design; 3–6 are the numbers and the UI; the rest are lifecycle and polish.
Record every INJECT result in `scripting_best_practices.md` § INJECT in the same session.
Lettered items came out of the final whole-branch review and sit beside the numbered item
they belong with; the numbering is stable so earlier notes that cite "checklist 7" or
"checklist 10" still point at the right thing.

**Structural — a failure here means the premium stack is not doing what the files say**

1. **Do `INJECT:`ed `modifier = { }` blocks SUM with vanilla's?** — **CONFIRMED: YES, every
   case.** Read in game by the owner on **2026-09-19** (country RANKS: the rank's −50% and
   its +50% cancel both gone from the interest tooltip; TECHNOLOGIES: the finance techs' −2%
   cancelled) and on **2026-09-20** (LAWS: laissez-faire's −25% and the mod's cancelling
   +25% both gone from the same tooltip). §17 checks 1, 3 and 4 are closed, and with them
   `te_monetary_rank_injections.txt`, `te_monetary_tech_injections.txt` and
   `te_monetary_law_injections.txt`. Recorded in `scripting_best_practices.md` § INJECT.

1b. **Check 2 — a FLAT KEY inside a static modifier** — **CONFIRMED 2026-09-20: it sums too.**
   `te_monetary_base_offset` is gone; vanilla's flat base is cancelled by
   `country_loan_interest_rate_add = -0.2` inside the mod's `INJECT:base_values` block
   (`common/static_modifiers/extra_modifiers.txt`). Day one on a fresh 1836 game the owner
   read **no "Base Value" line at all** on the budget-panel interest tooltip and
   country-specific rates, which is the "keys sum" branch of the tell; the failure branch
   (every country at 0.0%, i.e. a −20% base) did not happen, so nothing is reverted. This
   also retro-validates `state_expected_sol_from_literacy = -5` against vanilla's `+5`, the
   same shape shipped since April.

   **Day-1 dispatch and released subjects: CONFIRMED 2026-09-20 in the same read.** Rates
   were already country-specific on 1836-01-01 — so the hidden-country-event fan-out from
   `on_game_started` delivers with no delay (that is checklist item 7 as well) — and a
   **released subject shows its own rate**, not its former overlord's, so the
   country-creation hooks' `scope:target` dispatch resolves against the new tag. Both
   recorded in `scripting_best_practices.md` § ROOT-resolved multipliers.

   Still worth a glance, but no longer load-bearing: the five vanilla finance techs
   (`banking`, `central_banking`, `mutual_funds`, `international_exchange_standards`,
   `modern_financial_instruments`) should each still show `+10%` minting on their tooltip —
   `country_minting_mult = 0.1` sits in the same vanilla `modifier = { }` block R3 cancels
   the interest line in, and it needs no arithmetic to read.
2. **Does the country-scope `modifier:` read aggregate every source type?**
   `country_credit_standing_add` is granted from country **ranks**, an **institution**
   (`institution_national_bank`), a company **`prosperity_modifier`** (`company_shell`) and a
   PM **`country_modifiers`** block (`pm_shell_pernis_refinery`) — none of which is covered by
   the existing laws-and-techs precedent. Hover the dashboard's **Credit Standing** row as a
   great power, and again as a Shell owner: every one of those contributions must appear. If
   one is missing it vanishes silently.

2a. *(Removed.)* R3's cancel-INJECTs mean no vanilla finance tech moves the
   `country_loan_interest_rate_add` sum at all, so there is no window between the tech
   landing and the next pulse to check. Checklist item 1's minting read covers what is left.

**Numbers and UI**

3. **The §7.4 anchor table, within 0.5pp** (the phase-1 exit criterion). Expected from the
   shipped values: **Britain 1836 = 4.0%** (converging on 3.5% as the national bank fills),
   **USA 1836 = 6.5%**, **Siam 1850 = 20.0%**, late-game great power on the floor = **3.5%**
   (3.25% under CBI), same GP in a panic after default = **15.5%** plus up to 4pp of debt-load
   premium.
   **Non-anchor 1836 starts**, computed the same way and worth reading off the same save:
   **Russia = 12.5%** (great power, `stock_exchange` but no `banking`, no national bank),
   **France = 6.0%**, **Austria and Prussia = 8.5%**. Russia's 12.5 against vanilla's 10 is the
   one to look at: the front-loaded −4.0 on `banking` makes an unbanked tier-3 great power
   *dearer* than vanilla, which §7.2 did not intend (it accepts weak countries getting
   *cheaper* debt, not strong ones getting dearer). **Balance exit criterion: no 1836 country
   pays far above what it pays in vanilla.** Scan the great powers and the majors; if several
   sit well above, the remedy is the owner's call — this checklist only surfaces the numbers.
4. **Does a rate render with one decimal?** The `REPLACE:` of the `country_loan_interest_rate_add`
   *type definition* at `decimals = 1` is precedented but unseen.
5. **Does `GetValueWithBreakdownFor` render for the two new mod-declared modifier types?**
   Credit Standing and Risk Premium must each show an engine breakdown block under the
   script-computed lines. An *empty* breakdown is fine; a *missing* block means the accessor
   did not resolve.
6. **Walk the dashboard — CONFIRMED 2026-09-20 (owner, in game), except (e) digital currency and the digital −3 chart in (g), not yet walked. Also still open: confirm `te_rate_paid_rooted` is set on a country after its first pulse (`root ?= this`); if it never sets, the rate modifier is harmlessly re-applied every month.** (a) Fiat great power: policy rate one decimal, target an integer,
   `+` moves only the target and the rate follows ~0.33/month; the engine's rate figure and
   `te_rate_paid_pts` should differ only by the surviving vanilla `_mult` modifiers — an
   *additive* gap, or a ratio no percentage modifier explains, is the leak this pairing
   exists to expose. (b) Delegate, then take control; pick Growth and watch the target move
   on its own. (c) Enact CBI: no delegation button, dead stepper, mandate buttons still live,
   floor reachable at 0.25. (d) Gold standard: Peg Defence appears, target band is a 4–5
   point window around the reference rate, and **OMO is locked at every rate** with the
   convertibility line (`banking_omo_unbacked_money_tt`) as the only red cause — no floor
   line beside it. (e) Digital currency: the stepper reaches −3, and
   **OMO stays locked until the rate reaches −3, not 0**. (f) Four no-dial countries
   (bankless, commodity money, crypto, command economy): readouts plus exactly one
   cause-specific line, and no stepper / delegation / mandate rows. (g) History: two new
   charts, policy rate tracking target changes with about a quarter's lag and rate paid
   sitting above it by the premium; both tooltips print exact figures. (h) `debug.log` sweep
   for "Failed to fetch variable" bursts — the readiness gate should make them impossible.

6a. **No surface prints an exact `bubble_pressure`.** Sweep the banking panel, the dashboard,
   both history widgets and every banking tooltip for a bubble figure rendered to a decimal.
   Today all of them band it, and that is what keeps the hidden-state rule true: bubble is the
   one cycle variable `banking_cycle_advance_variables` gives no random nudge, and
   `banking_display_bubble_monthly_add` is exactly the modifier-driven part, so Δbubble minus
   the displayed monthly add is the stance push alone — `−0.75 × te_mon_stance_gap_clamped`,
   which two readings a month apart invert into the gap, and so into r\*, anywhere the gap is
   inside its ±4 clamp and bubble is off its own 0/100 bounds. If the vanilla panel's bubble
   bar (or anything else) turns out to show a number rather than a bar, **this stops being a
   checklist item and becomes an Important bug** — band it, or give `bubble_pressure` a random
   term.

6b. **OMO at a zero policy rate — CONFIRMED 2026-09-20 (owner, in game).** The fiat case item 6
   never states outright: with the policy rate down at its 0 floor the Open-Market Operations
   row goes green and the tool activates, so `te_mon_floor_threshold` /
   `te_mon_policy_rate_at_floor` do let the one regime that should reach the floor reach it —
   dropping `max = 0` did not shut the door on fiat along with gold. What is **not** confirmed
   is item 14's balance half: the retuned +1.5 bubble a month has still never been watched
   running, which needs a zero-rate recession to last a few months.

**Lifecycle**

7. **Day one is not vanilla's flat 20% — CONFIRMED 2026-09-20 (owner, in game).** 1836 rates
   are the mod's own country-specific numbers on day one, so the game-start pass runs: the two
   mod `on_game_started` declarations merge, and the no-delay hidden-country-event fan-out
   delivers before the player's first day (recorded in `scripting_best_practices.md` § ROOT-
   resolved multipliers). Nothing to move into `extra_on_actions.txt`.
8. **A pre-deletion save gets its 2 intervention points back** the month after loading, and
   the *Raise Policy Rate* row is gone from both dashboard lists.
8a. **Tag-switch into an AI great power.** Every AI country is held at `te_mon_delegated = 1`,
   so a human taking over an AI tag opens on **Delegated** with whatever mandate the AI's bank
   was running. That is truthful — the bank *was* driving — and one click of Take Control
   undoes it; the check is that the dashboard says so plainly, that Take Control works on the
   first click, and that a fresh Britain start opens **un**delegated by contrast.
9. **`random_country = { }` from `on_monthly_pulse`** (expected scope `none`) resolves — this
   is how the world reference rate is refreshed. Nearest precedent is `city_rank_on_action`
   running `ordered_state` from the same hook. **Observable, because a silent failure here is
   invisible**: the country-side self-heal seeds the global exactly once, so a broken
   `random_country` freezes the reference rate at 3.0 for the whole campaign rather than
   erroring. Run `te_debug_monetary.1` from the console the month after any great power
   finishes `macroeconomics` — "Reference rate" must read **2.5**, not 3.0.
10. **`round` / `ceiling` / `floor` / `min` / `max` behave as documented inside a
    `set_variable value = { }` block** (four sites). Related: `round(2.5)` — half-up (3) or
    half-to-even (2)? Either is inside every regime range and self-corrects on the first
    delegated pulse.
11. **An empty static modifier applied to a JE** — does `banking_stance_band_3` render as
    "Monetary Stance: Neutral" with no effects, or as nothing at all? Both are safe; the
    answer decides whether the neutral band should keep being applied.
12. **Revolution inheritance.** `je_banking_cycle` is `can_revolution_inherit`, so the entry's
    modifiers move but country variables do not. Worst traced case is **one month with no
    stance band** on the successor, not two stacked. Watch one revolution.
12a. **Releasing a subject does not move the parent's own rate.** The six release and uprising
    hooks update `scope:target`, the new tag, and deliberately *not* ROOT, which is the parent
    and already pulses monthly. Note a great power's policy rate, release a subject, and check
    it has not jumped by about a third of a point that same month (the drift step's per-call
    size) — that jump is the signature of a second, non-idempotent update in one month. The new
    tag should meanwhile open with a real rate rather than vanilla's ~20%.
13. **Relative order of global `on_monthly_pulse`, `on_monthly_pulse_country` and the JE's own
    pulse** (§17 check 7) — the stance reaches the cycle through a variable written by the
    country update and read by the JE pulse, so a one-month staleness is tolerated by design
    but has never been observed.

**Observer run (the rest of §19 row 1's exit criteria)**

14. No country sits at the 60 cap or at the 0.5 *total* clamp by accident; AI stance tracks
    the cycle; **mean AI stance gap ≈ 0 outside cycle extremes** (no regime permanently tight
    or loose); r\* is not recoverable from any tooltip. Also: the OMO retune (+1.5 bubble a
    month) is untested — it needs a zero-rate recession to fire at all.

### 0.4 Phase 2 as shipped — rulings, deviations and open checks

Phase 2 (§19 row 2) was implemented on `feat/monetary-policy-phase2` over ten tasks on
2026-09-20: inflation (core / headline / anchored expectations, the §9.3 basket), the rate
stack that reads it, monetisation and QE costs, the §9.2 bands and the hyperinflation chain,
§9.4 wage pressure and the real-wage dividend, §13 stance politics, the dashboard and history
rows, and a console harness for §19 row 2 — plus a final whole-branch review wave that
produced owner decision **G**, ruling **F-I2** and checklist items **27–35**. **Nothing below
has been seen in a running game either.** Every claim here is verified against the files;
every claim about *behaviour* is a simulation of the shipped equations or an argument from
them.

Phase 1's §0.3 checklist is **inherited unchanged** (ruling P10) — items 2–5, the unwalked
parts of 6 and 8–14 are still open and are not repeated here. The phase-2 list continues the same numbering from
item 15, so an older note citing "checklist 7" still points at the right thing. File
inventory and the new architectural rules: `mod_systems.md` § Banking Cycle →
**Monetary Policy (phase 2)**.

#### Owner decisions to review

Seven calls: A–F the run made and flagged rather than settled, and **G taken by the owner in
the final whole-branch review**. Each is one or two lines to reverse.

**A. "Inflation settles at 2 + P/c" is a simplification, and the shipped code is sharper
than §9.1 says.** With the real stance held, core converges on `expected + P`, so the
equilibrium inflation gap `g = π − anchor` has to satisfy `c_eff × g = P`, i.e.
`c × (1 − g/10) × g = P`. The left-hand side *peaks* at `g = 5`, where it equals **2.5 × c**.
So with the shipped de-anchoring `c_eff` there is **no fixed point at all** once
`P > 2.5 × c` — 0.625pp on a manual target (c = 0.25), 1.0pp delegated, 1.75pp under CBI. A
boom phase (+0.8) clears the manual threshold on its own. `2 + P/c` is the small-P
linearisation of the same equation with the de-anchoring factor dropped. This is *consistent*
with §9.1's own "a fixed manual target is unstable above the floor, by design" and sharper
than it: the instability is the credibility channel as well as the Taylor channel, and it
bites on a held **real** stance, not only on a pegged nominal one. The code is spec-faithful
and was not changed. Harness sequence 3 is where to watch it; the levers if the owner wants a
ceiling are `te_mon_deanchor_span` (the 10pp span) or a higher manual `c`.

**B. The growth mandate's `min()` cap binds at low inflation, so the two mandates coincide
there.** §6 asks for both "growth runs a point loose" and "growth is never more hawkish than
price stability". Together they mean `min(growth, price stability)`, and
`price_stability − growth = π − 1 + lean/2` — so the cap binds below ~1% inflation in a calm
cycle, ~2% in a downturn and ~2.5% in a panic, i.e. in exactly the conditions a player reaches
for the growth mandate. A consequence of §6's own two rules rather than a choice; the mandate
tooltip now states it in plain words. Dropping the cap is one line and re-opens the inversion
it exists for (at π = 0 with a panic lean, raw growth is 2.5pp *tighter* than price stability).

**C. A fiat regime enacted out of metallic money opens ~2pp loose for a few years.** At the
switch `π_core ≈ 0` while the anchor jumps 0 → 2, so a price-stability bank asks for
`r̂* − 2` and eases until inflation climbs to target — years, at α = 1/24. Accepted as a
realistic regime-change transient. **It is a transient of the *switch*, not of the 1836
start**: every tag starts metallic, so no tag is in this state on day one. (What day one
*does* look like is decision G below — not "every phase-2 term evaluates to zero", which is
what this paragraph used to claim.) One-line remedy if unwanted: seed `te_inflation_core` /
`te_inflation_expected` at `te_mon_inflation_anchor` on a regime change.

**D. With `banking_system_enabled` off, the AI monetises and the player cannot.** The
plumbing is deliberately never gated on the game rule, but the stepper lives on the
journal-entry dashboard, which is. Step 2's AI mandate rule has had exactly this shape since
phase 1. A capability asymmetry, not a script gate.

**E. Leaving dollarisation re-founds a currency and now pays for it.** §9.2 names no exit;
P9 invented the smallest one (the flag clears when the country next enacts a
`lawgroup_monetary_policy` law), and review found that made *dollarise → wait → re-enact
fiat* a currency reform with no pool wipe, no radicals and no premium. The exit now calls the
same shared effect the crisis's reform option does — **`te_mon_effect_new_currency`**:
headline / core / expected reset to 5, cost-push to 0, and `te_mon_currency_reform_premium`
(+5pp risk premium) for 3650 days. No pool wipe and no radicals at the exit, because the
months of −75% minting were that half of the price. The asymmetry is intended; whether it is
the right size is the owner's call.

> **How unequal it is, and what the levers are.** Dollarising and leaving costs the months of
> −75% minting — seigniorage is of order a few per cent of GDP a year in this model, so the
> whole dwell is single-digit per cent of one year's GDP — against currency reform's **100%
> investment-pool wipe plus radicals**, both immediate. The player who can wait is therefore
> buying the cheaper exit, and the shorter the dwell the wider the gap. Two levers if that
> reads wrong in play: a **minimum dwell** before the flag may clear, and a **fractional pool
> hit at the exit** (the reform's wipe scaled down) so the re-founding costs something the
> treasury feels. One thing that is *not* a leak: a monetary law imposed by script or by a
> revolution does not pass `on_law_enactment_pass`, so `te_banking_law_change_cleanup` never
> runs for it and the flag survives — the exit cannot be taken by accident. (There is a
> second exit since the final review: entering a **command economy** clears the flag for
> free. It is not a cheap way out of the price — a planned economy is not a dial — but it is
> the one path that leaves dollarisation without paying, and it is deliberate.)

**F. The inflation bands' expectations offsets are standing pressures that are never priced
in.** The owner's mid-run fact — an SoL *change* is absorbed into expectations over time, but
an SoL-*expectations* offset never is — applies to the band ladder as well as to the dividend
it was raised for. `te_inflation_band_elevated` / `_high` / `_very_high` / `_hyper` carry
`country_sol_expectations_lower_offset_add` at **+0.5 / +1 / +2 / +3**, standing for as long
as the band is, against `law_worker_protections`' +1 as the scale. +3 for a hyperinflating
country is deliberate; **+0.5 for an Elevated band a country can sit in for decades** is the
magnitude worth a second look. The real-wage dividend's −0.02 per unit (maximum ≈ −0.28) was
sized after the fact and sits comfortably inside the same scale.

**G. Phase 2 is NOT inert on an 1836 start — cost-push reaches every metallic country from
the second pulse. Taken, not flagged: keep the economics, add band hysteresis.** Three places
in this document and in the code said the opposite, and they were wrong (final-review finding
I1). What the code does:

- **Only the first pulse is inert in cost-push.** Step 6a seeds `te_basket_avg` to that
  month's index, so `index − avg = 0` and `te_cost_push = 0` exactly once.
- **From the second pulse** every country with a market carries
  `te_cost_push = 0.3 × (index − 36-month avg) × 100`, clamped ±6 — metallic ones included.
  §9.3's basket is gated on `te_mon_has_inflation` only for π, not for the index (ruling T2).
  A basket a few per cent under its own trailing average is an ordinary reading, and under a
  metallic regime expectations are pinned at 0, so *nothing offsets it*: a basket 3.4% under
  average puts a gold country in **Deflation**; a 10% grain spike cuts the rate it pays by
  roughly 0.9pp (headline is subtracted in step 7); and for a country with a dial it moves
  the displayed stance band and through it momentum, bubble pressure and step 8b's politics.
- **Core is not zero either.** Metallic money pins *expectations* and pulls core toward 0; it
  does not zero the rest of the pressure sum (deficit, cycle phase, bubble, the noise walk,
  any law or event pressure), so core settles where the pull and that sum balance.
- So **§7.4's anchor figures hold only ± the cost-push term**, not unchanged, and §0.3 item 3
  is a check against a moving number rather than a fixed one.

**The owner's call (2026-09-20) was to keep the economics spec-faithful** — the basket is what
§9.3 asks for and a metallic country genuinely did live with commodity-price swings — **and to
buy back only the UI churn it caused, with band hysteresis** (ruling F-I2 below). The three
one-line levers if play shows it too noisy, in increasing order of how much they change:

1. **Damp cost-push under `te_mon_is_metallic`** — multiply the term by a fraction inside
   `te_monetary_update_inflation`'s basket block. Keeps the direction, shrinks the amplitude.
2. **Take only core off rate paid** in step 7 (`subtract = var:te_inflation_core` rather than
   `var:te_inflation`). Removes the cost-push channel from the *rate* while leaving it in the
   band and the stance — which is arguably more correct anyway: lenders price the trend.
3. **Widen the hysteresis** past 0.25pp, which only buys quieter bands, not a quieter rate.

Checklist **27** is the in-game read of whether any of them is needed.

#### 0.4 rulings — deviations from, or bindings on, the sections below

Pre-flight rulings are P-numbered and were made before any code; the rest were made in flight
and are tagged with the task that raised them.

| # | Ruling | Why | Cost if wrong |
|---|---|---|---|
| **P1** | Implement the in-scope `(proposed)` items: §9.4 wage pressure + the real-wage dividend, §9.1's credibility `c` table including state-owned banking at 0.15, and §7.6's unanchored-expectations and monetisation premium terms | all are named in §19 row 2 or load-bearing for §10's tuning invariant | small terms to retune or remove |
| **P2** | Still deferred: §9.1's gold-supply term, §5.1's minting axis, CBI's 12-month mandate delay, France's commodity dial, estimation error shrinking with finance techs | owner undecided or phase 3; the plain regime pull `−π_core` carries the metallic deflation bias meanwhile | later additions, nothing to undo |
| **P3** | Monetisation is the **GDP-scaled `country_minting_add`** | §11 marks it chosen | swap to the `country_minting_mult` variant |
| **P4** | The deficit term annualises through a named `te_mon_deficit_annualise_factor` = **52**, and the computed deficit-%-of-GDP is printed in the console read-out | §17 check 12 is unverified; the engine docs make `income` weekly and `gdp` yearly, so 52 is the documented reading | one-line flip to 1 — **checklist 15** |
| **P5** | Step 6 (inflation) runs between steps 5 and 7 and reads **last month's** stance gap; step 8's real rate becomes `te_policy_rate − te_inflation` | forced by the step layout, and §16.3 already tolerates a one-month-old gap | one month of lag in two places — it is also why §10's war line comes out at 0.61% rather than 0.7% |
| **P6** | Every country except a command economy runs inflation | §4 makes bankless / commodity / crypto countries pay `era_base + own expected + 1`, so they need expectations even with no dial | performance; could be restricted |
| **P7** | A hidden mean-reverting walk `te_inflation_noise` (±0.1pp a month, bounded ±0.75pp) is added to the pressure sum, and core, noise, **`te_cost_push`** and the pressure **total** are never displayed | headline and expected are exact while `pressure` carries `−0.4 × stance_gap` with no random term — the same inversion §0.1 found for `bubble_pressure`. **Cost-push is hidden in practice and by rule** (final review, M1): nothing but `te_debug_monetary.1` prints it, and it must stay that way — headline is displayed and is core + cost-push, so with cost-push shown core becomes recoverable and the inversion opens | one term to delete |
| **P8** | §13's "sustained stance" keys on the **displayed band** (≤ 2 or ≥ 4 for six consecutive months), not on the true gap | a modifier appearing exactly at `\|gap\| ≥ 1` would print a bit of r\* | one trigger |
| **P9** | Dollarisation is a persistent flag variable, not a law; it clears when the country next enacts any `lawgroup_monetary_policy` law | the spec names no exit and this is the smallest one | small rework — and see T5's exit ruling below |
| **P10** | Phase 2 does not block on phase 1's open in-game checks, and inherits them | phase 1 is unverified but internally consistent. (The other half of this rationale as written — "every phase-2 term is zero on a metallic 1836 start" — is **false**, and is corrected in owner decision G: only the first pulse is inert, and from the second one cost-push moves the rate paid and the band of every country with a market. The ruling stands; its reason is now just the first clause) | — |
| **P11** | Wage pressure gets its **own** modifier type, `country_wage_pressure_add`; step 6 sums it with `country_inflation_pressure_add` | §9.4 and §11 would otherwise share one type, and the real-wage dividend could not tell a labour law from a devaluation | merge the two types back |
| **T1** | A bankless country falls through `te_mon_credibility_c` to the manual 0.25 | §9.1 has no bankless row, and a bankless country has no anchoring institution | one branch |
| **T1** | §9.4's "lower-strata loyalist trickle" to be delivered as `state_lower_strata_standard_of_living_add` | §9.4 promises a lower-strata gain, and an all-strata loyalists key would pay landowners for factory councils | — |
| **T6 (withdraws T1)** | **WITHDRAWN** — the ruling above is inert: the owner's fact is that **standard of living is an integer**, so a fractional `*_standard_of_living_add` does nothing unless it sums past a whole point. **Replacement:** `country_sol_expectations_lower_offset_add = −0.02` per unit on `te_mon_real_wage_dividend`, whose consumption chain is continuous end to end (`sol_expectations_lower_shift_value` → the multiplier on `sol_expectations_lower_strata_shift`) | verified against the files and against vanilla's own `tax_modifier_low/high`, which ship ±0.5/1.5 on the expectations key | ~31 other fractional-SoL sites in the mod are inert for the same reason — filed as **issue #338** (audit + content pass), deliberately not fixed here |
| **T2** | The §9.3 basket runs **before** the `te_mon_has_inflation` gate, for every country with a market | a command economy leading a customs union would otherwise starve its members of an index, and would book decades of price drift as one cost-push shock the month it liberalised; §14's exclusion is about π, not about the market's price index | move one block |
| **T2** | The noise walk's `random_list` **draw** is narrowed to `te_mon_has_dial` countries; its **decay** is not | §0.1's precedent (~1,330 wasted draws a month), and a no-dial country's pressure sum carries no r\* to hide. The decay stays ungated because every country *reads* this term, so a frozen draw would be a permanent ±0.75pp bias rather than harmless dead state | one limit |
| **T2** | **§9.1's "settles at 2 + P/c" is a simplification** — with `c_eff` de-anchoring there is no fixed point when `P > 2.5 × c`. Code left spec-faithful | consistent with §9.1's own instability paragraph, but sharper; **owner decision A** and the §9.1 pointer note | analysis only, nothing to revert |
| **T3** | Ratified: `te_mon_inflation_anchor` replaces the literal 2 in the price-stability reaction (`te_mon_mandate_price_reaction`) and in the unanchored premium (`te_mon_expectation_gap_abs`) | §9.1 gives the anchor as 0 under metallic money, so a literal 2 would make a gold-standard bank target `r̂* − 2` against its own pinned zero inflation | two constants back to literals |
| **T3** | The growth mandate's `min()` cap binds at low inflation, and is kept | spec-faithful consequence of §6's own two rules; **owner decision B** | drop the cap |
| **T3** | A fiat regime enacted out of metallic money opens ~2pp loose for a few years, and is kept | a realistic regime-change transient, and no 1836 start reaches it; **owner decision C** | seed core / expected at the anchor on a regime change |
| **T4** | The two law-event minting modifiers get **unscaled companions** `monpol_currency_stability_pressure` / `monpol_currency_devaluation_pressure` (∓1.0pp) rather than a pressure field of their own | all six sites apply the originals with `multiplier = sv_money_flow_event_small` (≈ `gdp × 0.0001`), and the engine multiplies **every field** of a modifier by the multiplier — a 1pp pressure field would have become thousands of points | two modifiers |
| **T4** | Event #40 is **retitled** "The Spectre of Runaway Prices", not gated on `te_inflation ≥ 20` | it fires while the country is *enacting* `law_fiat_currency`, so a 20% gate would be near-unreachable; the event was always an anticipation, not an observation | loc revert |
| **T4** | The AI monetises while the player's stepper is hidden under `banking_system_enabled = no` | same shape as step 2's AI mandate rule; **owner decision D** | gate step 1b on the rule |
| **T5** | Dollarisation is the **seventh state of the band modifier**, not a modifier stacked on one — and **dollarising resets headline, core *and* expected inflation to `te_mon_inflation_anchor`** | chosen from inside the hyper band, the two `country_minting_mult` fields would have summed to −1.55; one swap with one owner leaves no window at all, where an event-applied modifier or a "reset π so the band falls" rule both leave up to 30 days. A *partial* reset was tried on paper and rejected: with `expected` left at 50, the dollarised `−core` pull's fixed point `core = expected/2` climbs straight back to ~25 and the country spends years in *Very High* under a modifier saying inflation is somebody else's problem. Resetting both lands it at band 2 and holds it there | — |
| **T5** | Leaving dollarisation calls the shared `te_mon_effect_new_currency` (reset to 5 + `te_mon_currency_reform_premium` for 3650 days); no pool wipe and no radicals at the exit | otherwise the P9 exit was a free currency reform; **owner decision E** | four lines at the exit site |
| **T5** | `te_mon_hyper_cooldown` is cleared by the two **resolving** options, not by the exit | it is an anti-nag device for riding the crisis out, not a lock-out | two lines |
| **T5** | A dollarised country takes the metallic **pull** (`−π_core`) without the metallic **pin**, so the model's fixed point is `core = expected/2` rather than 0 | accepted for phase 2: with dollarise's full reset it lands near 1% and stays there | **Decided 2026-09-20 (§0.5 owner decision K):** it takes a pin, at the anchor (2) rather than metal's 0 |
| **T7** | `te_mon_stance_months` is capped at ±11 | §13 names no cap, and without one a decade-long stance takes a decade of the middle band to unwind. 11 makes the fade exactly as long as the climb — six pulses each way | one constant |
| **T7** | Rural Folk: `cross_of_gold_currency` added to `ideology_isolationist` | `ideology_particularist` already carried `simple_currency`, which cancelled the Cross of Gold on `ideology_agrarian` **exactly**, so §13's marquee row netted zero on gold and zero on fiat. Isolationist is a Rural Folk baseline held by no other IG, and a convertibility promise binds the rate dial to an external discipline nobody at home voted for — submitting the currency to the outside world is what an isolationist objects to | one line of generator input |
| **T7** | Petite Bourgeoisie: `simple_currency` added to `ideology_patriotic` | `ideology_meritocratic`'s pre-existing `advanced_curency` left PB coming out pro-digital. **Side effect accepted:** patriotic is also an Armed Forces baseline, so the Armed Forces gain a modest hard-money lean — correct on its own terms (fixed salaries and pensions), and §13 already puts them on the losing side of its own inflation row | one line |
| **T7** | `ideological_opinion_impact` stays **0** on `lawgroup_monetary_policy` | it scales the *legitimacy* friction between disagreeing governing IGs, not the IG approval §13 wants, which runs off `IG_APPROVAL_FROM_LAW` / `IG_APPROVAL_FROM_LAW_CHANGE` and is ungated by it. **Inferred from the defines, not observed** — **checklist 17** | one value (0.25, like the mod's other economy law groups) |
| **T8** | The `GetCustom`-in-`is_valid` single-cause line is kept, with no static fallback | precedent: `iw_funding_not_max_tt` uses a data function in an `is_valid` tooltip | ~40 lines of `trigger_if` branches — **checklist 21** |
| **T8** | A no-dial or command country sees two **greyed** monetise buttons rather than a pure readout | consistent with the target stepper, which already behaves that way | a visible gate |
| **T9** | The harness's three extras are accepted: a seed option (a third console-only writer of inflation state), a peace option, and a pin that also takes state-owned banking off | required to reproduce §10 at all — an 1836 country pinned at target 5 with π ≈ 0 measures a *disinflation*, not the fixed point — and state-owned banking's `c = 0.15` is not the manual 0.25 every number in the harness header assumes | delete the options |
| **F-I2** | The §9.2 band edges are **hysteresised by `te_mon_band_hysteresis` = 0.25pp**: a country leaves the band it is in only once headline is a quarter point past the edge, so the live boundary sits at `edge + 0.25` for a country climbing and `edge − 0.25` for one falling, decided from last month's `te_inflation_band` through `te_mon_band_test_*`. A country's very first pulse uses the plain edges (`te_inflation_band_applied = 0`), because its band is step 0's seed rather than an observation. The **hyper** edge is un-hysteresised on the way up, so the crisis still fires at exactly 50 | the band is a state machine with five consumers (the modifier swap, the real-wage dividend, the crisis, the dashboard row and its tooltip) and headline is noisy — `te_inflation_noise` alone is a ±0.75pp walk — so plain edges make a country parked near an edge swap all five every second or third month for no change in its economy. Bought instead of damping the economics (owner decision G) | one constant |

#### Deferred (phase 2's additions to §0.2)

- ~~**The dollarised regime pull has no expectations pin** (T5 above) — a phase-3 decision.~~ **Decided and shipped with phase 3** — §0.5 owner decision K.
- **The §9.1 gold-supply term and §12.2's gold-flow pressure term** are absent from the
  pressure sum, as P2 and §19 row 3 intend.
- **The §9.2 flavour notifications** (a one-shot on first *High*, one on first *Deflation*)
  were skipped: each needs its own "first, not every crossing" variable plus loc and wiring,
  and nothing depends on them.
- **§13's "CBI endorsed by Industrialists and Petite Bourgeoisie" needed nothing.**
  `law_central_bank_independence` lives in `lawgroup_financial_regulation`, and all eleven
  `finreg_*` stance lists in `ideology_modifications.py` already carry a stance on it
  (`finreg_laissez_faire` approve, `finreg_market_liberal` strongly_approve, and so on).

#### Known roughnesses (phase 2)

All judged acceptable for a first pass; listed because each is user-visible or behavioural.
Four of them (5, 7, 8 and half of 9) were **fixed in the final whole-branch review** and are
struck through rather than deleted, so a note citing "roughness 8" still points at the right
thing.

1. **Two band fields are journal-entry-gated by construction.** The Deflation band's
   `country_finance_momentum_monthly_add = −0.2` and the Very High / Hyper bands'
   `country_bubble_pressure_monthly_add` are consumed by `banking_cycle_advance_variables`,
   which only runs for a holder of `je_banking_cycle`. A bankless country in deflation gets
   the §10 rate rise and the political anger but no momentum drag. Every other field in the
   ladder is always live.
2. **The AI's monetisation level escalates by snapping and only retreats by a step.** Step 1b
   *sets* the level to 1 or 2 as the war / debt / bankruptcy tests flip, and subtracts 1 a
   month otherwise — so 3 → 1 in one month is possible while 1 → 0 takes one. The comment
   beside it reads as though both directions were gradual.
3. **Landowners' hard money is gold-only.** `simple_currency` is *neutral* on
   `law_commodity_money`, so the IG §13 casts as the hard-money constituency has no opinion
   about the regime every country starts on.
4. **The two premium rows render `|1`, not `|=+1`** — `0.3%` rather than `+0.3%` in a column
   of signed lines.
5. ~~**The Expected Inflation tooltip omits the mandates half-line.**~~ **Fixed in the final
   review wave** — `banking_dash_mon_expected_tt` now says a delegated bank steers on the
   underlying trend, not on this figure.
6. **An ineligible monetisation step shows a cause line *and* a range line**, not literally
   the one line the design asks for.
7. ~~**The Price Band row tells a command economy it "sits in no band".**~~ **Fixed in the
   final review wave** — `banking_dash_price_band_cost_command` now says its band is
   nominal. (`banking_mon_monetise_step_tt`'s "twice as quickly" was also listed here and is
   **correct**: α is 1/12 under a CBI against 1/24 delegated, exactly 2×. The ~1.75× that
   prompted the note is the *credibility* ratio, 0.7/0.4, which is a different sentence.)
8. ~~**Two naming mismatches.**~~ **Both fixed in the final review wave** — the dashboard row
   is now labelled "Inflationary Pressure" to match the modifier type, and
   `te_history_banking_effects.txt`'s header says **six** metrics, which is what its own list
   and its six `te_history_record_sample` calls carry (three cycle, three monetary).
9. **Harness pin.** On a command economy that also holds state-owned banking the pin lands on
   `law_directed_credit_development_banks` rather than universal banking — the
   `on_law_activated` consistency sweep bounces state-owned banking the moment the country
   stops being a command economy, before the pin's own step 3 is reached. The behaviour
   stands (directed credit is neither credibility anchor, so the pin still holds and `c`
   still falls through to the manual 0.25); the final review corrected the code comment and
   `.5.d`, which claimed universal banking. What the country does not get is universal
   banking's `country_banking_random_momentum_mult` of +0.10 — directed credit runs −0.2, so
   the financial cycle is quieter than the harness header describes. And `law_anarchy` /
   `law_factory_councils` / `law_women_in_the_fields` countries have **no** stable
   economic-system landing for the pin at all; the pin's own verify catches that and tells
   the player to fix it by hand.
10. **A dollarised country's Price Band and Inflation rows disagree by design.** The band row
    reads "Foreign money" while the Inflation row keeps printing a live figure, because the
    loop runs for every non-command country and only the band *modifier* is replaced (P9).
    The tooltip explains it.
11. **Core inflation is clamped −10…100 like headline**, so a country pinned at the ceiling
    has a headline that stops responding to cost-push. Unreachable in practice — the §9.2
    crisis fires at 50 — but the spec does not describe the corner.
12. **The real-wage dividend can be swallowed by an empty expectations sum.** The `±0.1` gate
    in `sol_expectations_effects.txt` tests the *total* shift, so a −0.04 offset with no other
    contributor does nothing. Any country that earns the dividend holds a labour law carrying
    +0.5 or +1 of its own, so in practice the sum clears easily.

#### IN-GAME VERIFICATION CHECKLIST (phase 2)

Continues §0.3's numbering, and ordered the same way: by **how much breaks if the check
fails**. 15–17 can invalidate a whole mechanism; 18–23a are the numbers and the UI; 24–26 are
the harness and the exit criteria; **27–35 were added by the final whole-branch review**, and
27 belongs with 15–17 — it is the check on owner decision G. Phase 1's items 2–5, the unwalked
parts of 6 (digital currency, and the digital policy-rate chart — see item 22) and 8–14 are
still open and are inherited, not repeated.

**Structural — a failure here changes what the phase does**

15. **Deficit units (ruling P4 / §17 check 12).** `te_debug_monetary.1` prints
    **`te_mon_deficit_pct`**, the *annualised* figure. A real deficit is a few percent of GDP;
    a reading in the **hundreds** means the budget flows were annual already and
    `te_mon_deficit_annualise_factor` must be flipped from 52 to **1** — one line in
    `te_monetary_script_values.txt`. Left wrong, a 2%-of-GDP deficit contributes
    `0.3 × (104 − 1) ≈ 31pp` of standing pressure, i.e. instant hyperinflation for half the
    world. Documentary support for 52: `docs/engine/event_targets_summary.txt` documents
    `income` as **weekly** and `gdp` as **yearly** (`total_expenses` is documented only as a
    trigger and is assumed to share income's cadence). The same observation settles §17 check
    12's other half, whether the existing fiscal-policy input is live at all. **Do not flip
    `te_mon_weeks_per_year` with it** — that 52 is a fact about `country_minting_add` and is
    deliberately a separate constant.
16. **`mg:<good>` in a market that never traded the good (§17 check 10, §9.3).** The basket
    gates each of its eight goods on
    `market ?= { mg:<good> = { market_goods_sell_orders > 0 } }`, but `te_debug_monetary.1`'s
    basket section prints all eight `te_mon_price_rel_*` reads **ungated on purpose**: an
    engine complaint against one of those lines in `debug.log` *is* the answer, and the gated
    index printed beside them shows what the model actually used. Fire `.1` as any 1836 tag
    (nobody trades oil) and sweep `debug.log`. If the ungated read errors, the model is still
    right — it is the probe that has to move.
17. **Does an IG law stance on `lawgroup_monetary_policy` reach IG approval at all?** All of
    §13's Part B — **20** ideology assignments added on this branch, **24** entries in
    `ideology_modifications.py` carrying a `lawgroup_monetary_policy` stance in all — rests on `ideological_opinion_impact = 0`
    gating only the legitimacy friction and not `IG_APPROVAL_FROM_LAW`, which was inferred
    from define names and `vanilla_politics_reference.md`, never observed. Enact a monetary
    law with a stanced IG in government and look for a line for that law in the IG's approval
    tooltip. If there is none, the one-line fix is to set the group to 0.25 like the mod's
    other economy law groups. (Worth a second read while there: an IG already pinned at
    vanilla's global `MAX_IG_APPROVAL_FROM_LAWS` ±5 absorbs these ±1 rows entirely.) While
    on the politics: step 8b's own swap should issue cleanly month to month, its ±1 rows
    should read sensibly in the IG approval tooltip, and six months should feel like a
    policy rather than a meeting.

**Numbers, modifiers and the UI**

18. **The real-wage dividend's expectations path, end to end.** Step 6d applies
    `te_mon_real_wage_dividend` with `multiplier = var:te_mon_wage_dividend_applied` — a
    country-held modifier scaled by a variable, gated on `root ?= this` — and its
    `country_sol_expectations_lower_offset_add = −0.02` per unit is summed into
    `sol_expectations_lower_shift_value`, which is itself the **`multiplier` on
    `sol_expectations_lower_strata_shift`, a country-held modifier carrying the state-masked
    `state_lower_strata_expected_sol_add`**. On a comfort-band country with labour laws:
    confirm the lower-strata expected-SoL line in a state panel actually moves. The modifier's
    own tooltip renders "+0" at `decimals = 1`, so read the state panel, not the tooltip. Two
    band-edge behaviours ride along and have only been reasoned through: the dividend
    arriving and departing as the band crosses into and out of comfort, and the wage-price
    spiral's doubling switching on at the *High* edge (it reads last month's headline, ruling
    P5). `te_debug_monetary.1` prints every input for both.
19. **The band modifiers' state- and interest-group-masked keys, applied at country scope.**
    `te_inflation_band_high` and above carry `state_tax_waste_add`, both
    `state_*_investment_pool_efficiency_mult` keys and three `interest_group_ig_*_approval_add`
    keys, all relying on propagation from a country-scope `add_modifier`. Precedent is solid
    on both sides (vanilla applies `outmoded_bureaucracy` to TUR at country scope; the mod's
    `banking_crash_intervention_nationalize` mixes all three masks) but unread for these. On
    the first save that reaches Elevated or High, hover the modifier and check every field
    lands.

19a. **Monetisation's three reads.** That the budget panel's minting line moves by roughly
    1% of annual GDP a year per level (the debug event prints the level and the applied
    weekly amount beside it); that an AI at war with `scaled_debt ≥ 0.5` actually reaches
    level 1; and that the six law-enactment events in `extra_law_events.txt` now show a
    **second, unscaled** inflation-pressure modifier beside the minting one.

20. **The hyperinflation flow.** The band swap across a boundary; the crisis firing **once**
    (24-month cooldown, cleared by the two resolving options); the reform option's pool wipe,
    radicals and ten-year premium; the dollarise option landing at
    `te_inflation_band_applied = 7` with the band back at 2 on the next pulse; and the P9
    exit paying `te_mon_effect_new_currency` on the next monetary-law enactment. One engine
    form rides along and is genuinely untried: `add_investment_pool` with a **negative**
    script value, which should land the pool at 0 rather than below it (the value is exactly
    `−investment_pool`, on the mod's own `ce_pool_withdraw_pool_cost` precedent). *(The
    task-5 report also flagged the bare `custom_tooltip = te_inflation.1.a.tt` form with a
    **dotted** loc key as unprecedented. It is not: `events/irredentism_events.txt` uses the
    same bare-dotted form three times — `irredentism.1.b.tt`, `.1.c.tt`, `.2.a.tt`, all with
    loc present. Nothing to check.)*
21. **`[GetPlayer.GetCustom('…')]` inside an `is_valid` `custom_tooltip`** — the greyed
    monetisation buttons' single cause line. The in-repo precedent
    (`iw_decrease_funding_effect_tt`) is an **ExecuteTooltip** path; this is
    `IsValidTooltip`. If it renders blank, the fallback is five static-key `trigger_if`
    branches per op — mechanical, ~40 lines, nothing else changes.
22. **Both charts with a negative-minimum axis.** The new inflation chart (−4…12, drawn 0%
    line at `position = { 0 -27 }`) and — never looked at either — **phase 1's digital
    policy-rate chart** (−3…12, its own 23px offset; §0.3 item 6(e)). Neither offset can be
    checked from the files. Also confirm a deflation month draws a visible sliver rather than
    nothing, a ≥ 12% month draws a full bar, and both tooltips print the exact figure.
23. **`ScriptValue(…)|=+1`.** Three rate-paid rows use the signed script-value formatter; the
    repo has precedent for `Var().GetValue|=+1` and for `ScriptValue()|1` separately, never
    for the two together. A missing or unsigned figure on those rows is the tell.

23a. **A glance at the console read-out, because checks 15, 16 and 24 all read their figures
    through it.** `te_debug_monetary.1`'s new sections use
    `SCOPE.GetRootScope.ScriptValue(…)`. This is a **confirmation, not a risk**: the same
    accessor already renders in four `country_event` descriptions in this mod —
    `environmentalism_events.1`–`.4`, which print
    `[SCOPE.GetRootScope.ScriptValue('temperature_anomaly_display')]`. If the pressure or
    basket block nevertheless comes out blank, the fix is one find-and-replace to
    `GetPlayer.MakeScope.ScriptValue`, correct for every use of the event except firing it at
    a foreign tag from the console.

**The harness, and §19 row 2's exit criteria**

24. **The three console sequences, with their expected numbers.** They are written out in the
    header of `events/te_debug_monetary_events.txt`; run them after `te_debug_monetary.5`
    option (a) pins a fiat tag to a manual target.
    - **§10's fixed point.** `.7.a` (seed) then `.6.a` (12 pulses): policy 5, π 2, expected 2,
      market yield 5, rate paid **5.0%** — held indefinitely. Take the baseline **after** the
      pin, not as a literal 5.00: the pin's move off CBI or state-owned banking raises the
      structural premium by up to 0.5pp and swings
      `country_banking_random_momentum_mult` from −0.10/−0.35 to +0.10.
    - **The never-disinflate invariant.** `.7.b` (monetisation 3, target 5) → `.6.a` twice →
      `.7.c` (peace, dial untouched) → `.6.b` three or four times. Simulated on the shipped
      equations: headline peaks at **12.7** with expected lagging at **6.5**; rate paid at the
      war trough **≈0.61%** with the 0.5 clamp binding for a few months; rate paid averages
      **≈5.85%** over the following 21 years against **5.00%** before the war — never below
      the baseline, which *is* the invariant; headline climbs 12 → ~20.7 over twenty years and
      the band reads 5, never 6.
    - **The §9.1 drift check.** On a pinned manual target (c = 0.25), any standing pressure
      above **2.5 × c = 0.625pp** — a boom phase alone clears it — should produce inflation
      that never settles (owner decision A). Slow by design: e-folding in years.
    `.6` stops the month the crisis fires (its loop tests
    `te_mon_hyper_cooldown < te_mon_hyper_cooldown_months`). Two forms in the harness are
    themselves unverified: a hidden option (`trigger = { }` on `.7.b`) leaving three visible
    options, and the `first_valid` title pair that reports a failed pin.
25. **§19 row 2's observer run.** 50 years: median fiat inflation **1–4%**, including AI banks
    on the growth mandate (at war or `scaled_debt ≥ 0.5`); no oscillation with a period under
    three years; at least one organic hyperinflation and one deflation. Plus the judgement
    half — the never-disinflate path must be worse **overall** than disinflating over 15
    years, judged on treasury, SoL and radicals, *not* on rate paid alone, where it is
    deliberately the cheaper line (§10).
26. **Hidden-state sweep, including P7's noise and cost-push.** No surface may print
    `te_inflation_core`, `te_inflation_noise`, **`te_cost_push`** or the pressure **total** —
    on top of §0.3's list (`te_neutral_rate`,
    `_error`, `_walk`, `te_mon_stance_gap`, momentum, and `bubble_pressure` to a decimal,
    item 6a). Exact by contract: headline, expected, the five band edges, the monetisation
    level, and the two player-chosen pressure modifier types. Sweep the six new dashboard
    rows, the band tooltip's edge ladder, both `GetValueWithBreakdownFor` breakdowns, the
    inflation chart tooltip and the crisis event. `te_debug_monetary.1` is the one place the
    hidden values may be printed, and `.5`'s pin and `.7`'s seed are the only console writers
    of them.

**Added by the final whole-branch review**

27. **What cost-push actually does to a metallic 1836 country (owner decision G).** The
    structural one. Play **GBR** and one commodity-money minor from 1836 to 1846 and record:
    the **min and max of rate paid** against §7.4's anchor figure for that tag (3.5% for
    Britain), how many **months are spent in Deflation or Elevated**, and — for Britain,
    which has a dial — how often the **displayed stance band flips with the target
    untouched**. `te_debug_monetary.1` prints `te_cost_push`, `te_basket_index` and
    `te_basket_avg` beside the rate, so a swing can be attributed. If the rate paid wanders
    by more than about a point either side of the anchor, or a gold country spends most of a
    decade in Deflation, decision G's three levers are the answer, in the order it lists
    them.
28. **How often the band actually swaps, with the hysteresis in (ruling F-I2).** Count band
    changes per decade for a country parked near an edge — Elevated/Stable is the common
    case. A handful a decade is the intended behaviour; one every two or three months means
    0.25pp is too small against `te_inflation_noise` and the constant goes up. Watch the
    real-wage dividend arrive and depart with it (checklist 18 is the other half), and
    confirm the crisis still fires at exactly 50 on the way up.
29. **Does `country_minting_mult` scale `country_minting_add`?** The §9.2 ladder's minting
    penalty (−0.3 at *Very High*, −0.8 at *Hyper*) and `te_mon_dollarised_modifier`'s −0.75
    are all `_mult`, while §11's monetisation is `country_minting_add`. If the engine applies
    the mult only to the *base* minting and not to script-added minting, **monetisation is
    immune to the band's penalty** — which is exactly the feedback the ladder exists to
    provide, and the never-disinflate invariant is measured with it missing. Read the budget
    panel's minting line at monetisation 3 with and without the *Hyper* band and compare.
30. **Bankless fiat AI countries drifting to the crisis.** A country with fiat money and no
    national bank has no dial, so its stance term is 0, its `c` falls through to the manual
    0.25, and owner decision A's threshold `P > 2.5 × c = 0.625pp` is cleared by a boom phase
    alone — with nothing able to lean against it. Sweep a 50-year observer run for tags in
    band 4+ that never held a national bank. If there are many, the answer is a floor on `c`
    for no-dial countries or a regime pull for them, not a retune of the pressure terms.
31. **AI monetary-law churn, and dollarised AIs getting out.** 24 `ideology_modifications.py`
    entries now carry a `lawgroup_monetary_policy` stance (checklist 17), which changes what
    the AI's law-selection weights see. Watch for a tag re-enacting monetary laws every few
    years, and — separately — whether an AI that dollarises ever takes either exit (a
    monetary law, or a command economy). A dollarised AI that never leaves is a tag
    permanently at −75% minting; that may be right, but it should be observed rather than
    assumed.
32. **What a revolution, a civil war or a tag formation inherits.** Country variables and
    country modifiers do not travel together. The band modifier, the §13 stance-politics
    modifier, `te_monetisation_minting` and `te_mon_real_wage_dividend` are all held on the
    country and all driven by an `_applied` bookkeeping variable, so a successor tag that
    inherits one without the other lands in a state the swap cannot repair. **Look
    specifically for two band modifiers on one country**, and for a minting or dividend
    modifier with no variable behind it. Trigger a revolution and a formable unification and
    read the successor's modifier list against `te_debug_monetary.1`.
33. **The empty `te_inflation_band_comfort`, on roughly every tag in the world.** It is
    applied deliberately (step 6c always has exactly one thing to apply, and the modifier
    list always names the band), but an empty `modifier = { }` on ~1,400 countries is a form
    nothing in this mod has tried at that scale. Check `debug.log` for a complaint about it
    at game start, and look at how it renders in the country's modifier list — a nameless or
    zero-line entry there is worse than no entry.
34. **What step 9 now costs every month.** Cost-push moves the rate paid for most countries
    with a market every pulse, so step 9's 0.05pp skip threshold no longer spares them and
    the interest modifier is removed and re-added roughly `N_countries` times a month. Time a
    late-game month against a pre-branch save of the same campaign, and watch the first of
    the month specifically — that is when the country pulse runs. If it bites, the lever is a
    larger skip threshold in step 9, not fewer pulses.
35. **The repeat-reform loop has to be worse than not doing it.** Monetise to 3, hyperinflate,
    take the currency reform, monetise again. Each pass costs a 100% investment-pool wipe,
    radicals and ten years of `te_mon_currency_reform_premium` — and the premium **refreshes
    rather than stacks**, which is the thing to confirm: if a second reform inside ten years
    only resets the clock on +5pp rather than adding to it, check that the pool wipe and the
    radicals are still enough to make the loop a losing line. Judge it the way §19 row 2
    judges the never-disinflate path: on treasury, SoL and radicals over the whole run, not
    on rate paid.

### 0.5 Phase 3 as shipped — rulings, deviations and open checks

Phase 3 (§19 row 3) was implemented on `feat/monetary-policy-phase3` on 2026-09-20: the real
world rate (§12.1), gold flows with hot money and the price–specie term (§12.2), peg
confidence and the convertibility crisis (§12.3), the peg-defence mandate's real formula (§6),
the dashboard rows and a console harness for §19 row 3. **Nothing below has been seen in a
running game either** — phases 1 and 2's open checks are inherited unchanged (ruling P10's
logic), and the checklist continues from item 36. File inventory and the architectural rules:
`mod_systems.md` § Banking Cycle → **Monetary Policy (phase 3)**.

**What §19 row 3 lists that phase 3 did *not* have to do.** "Regime law stances" shipped with
phase 2 (§13 "Delivered"; rulings T7). "FX buttons unchanged" is row 3's own interim rule, so
`cb_fx_support`'s possibly sign-wrong `banking_stance_is_tight` weight (§0.2) stays a
**phase-4** item despite that note calling it the "phase-3 FX pass". §0.2's line about phase 3
revisiting the AI's better-informed tools "when IGs start reacting to the stance" is moot: the
stance politics shipped in phase 2, keyed on the displayed band.

#### Owner decisions (phase 3) — H, I and K decided, J resolved by the hybrid model

**H. DECIDED 2026-09-20 — nobody faces a world rate that contains itself.** As first shipped,
a lone discretionary great power (a *player* Britain in 1836) **was** the world rate: its gap
was 0 by construction, so it had no flows and no peg. The owner's call: each member of the
average records its exact share of the two accumulators at refresh time
(`te_mon_world_own_num` / `_den`), and step 0 subtracts it, so a great power faces the **rest**
of the world's rate — the reference rate when there is no rest — while everybody else still
sees the full average, hegemon included. A player Britain in 1836 therefore faces 3.0.
*Considered and parked for after playtesting:* widening the average to non-great-powers (adds
price-takers, and nobody at all in 1836 — Britain is the only tag on gold with a bank), and
the owner's observation that **commodity money also moves gold** — specie circulates and is a
trade good under bimetallism too — so flows arguably belong to commodity-money countries as
well. That is §5.4's open France question from another side, and would want a dial (or at
least a flow) for commodity money + national bank.

**I. DECIDED 2026-09-20 — borrowed gold pays the policy rate.** The owner's question was what
stopped real countries doing this, and the answer is the carry: gold drawn in by Bank Rate
came as short-term balances *earning* that rate, against a vault that earns nothing. So
`te_gold_hot_money` now costs `te_policy_rate / 12` percent a month (`te_gold_carry`) — paid by
`add_treasury` while there is a treasury, **capitalised into the balance** when there is not,
so not paying is never free either. That makes hot money strictly dearer than ordinary
borrowing for any country with sound credit: at world + 5 on an 8% rate, one reserve limit
costs 1.6% of GDP a year for as long as it is held. It stays what it historically was — a way
to refill a vault or defend a peg. Ruling Q8's cap is kept as a backstop. The carry is not part
of `te_gold_flow`, so the price–specie term prices the principal only; a suspension freezes
the balance **and** the carry.

**J. RESOLVED by the hybrid model (below) — was:** An indebted AI on gold sits a point above the world rate, permanently. Ruling Q5's
shortfall term treats any debt as an empty vault, so the peg-defence target is world + 1 for
every AI gold country in debt — a standing −0.125 of momentum a month. That is "the cost of
the peg" §8 promises, and it is what keeps its confidence from eroding, but AI debt is the
normal state of many tags. The lever is the 2pp in `te_mon_peg_shortfall_pp`. **It also moves a phase-1 expected number:** a peg-defending AI that is *in debt* now targets `ceiling(world + 1)` = 4 rather than 3, so §0.3 item 3's anchor figures (Britain 1836 at 4.0%) read a point higher for any AI gold country that starts, or falls, into debt. *(No longer true: the shortfall reads the bank's vault, and debt is not in it.)*

**K. DECIDED 2026-09-20 — a dollarised country's expectations are pinned at the anchor.** This
closes the item ruling T5 (§0.4) left open. It keeps the metallic pull and gains a pin at
`te_mon_inflation_anchor` (2, not metal's 0 — the adopted money is somebody's managed
currency): imported credibility is the whole of what dollarising buys, and unpinned, a
dollarised country with a large deficit drifted its own expectations up for a currency it
does not issue. Core now settles near `1 + P/2`. One `else_if` in step 6's expectations block.

#### 0.5 rulings — deviations from, or bindings on, the sections below

| # | Ruling | Why | Cost if wrong |
|---|---|---|---|
| **Q1** | The world rate is clamped to **−2…10**, is **not smoothed**, and reads whatever each great power's last pulse left | §12.1 gives no bounds; a no-dial rate is `world + expected + 1` and a gold gap `policy − world`, and neither means anything at −8. No smoothing because its inputs already move at ⅓pp a month; the pulse order is §17 check 7, unknown, so a one-month-old input is tolerated by construction | two constants; a partial-adjustment line in `te_monetary_refresh_world_rate` |
| **Q2** | **`era_base` survives** as the reference rate: it is still the base of the neutral rate (§8), the lenders' floor (§10, §21) and every seed. The world rate replaced it in exactly three places — the no-dial derived rate (§4), peg defence (§6) and the gold gap (§12.2) | §10 and §21 name `era_base` for the floor explicitly; putting a GDP-weighted *policy* figure under the neutral rate would make r\* partly public | one variable name per site |
| **Q3** | The phase-1 gold band (reference ±2) is **deleted**; gold's range is §5.1's 0–15. The dashboard keeps **both** rows — *World Reference Rate* and the new *World Rate* — because the first is still the lenders' floor | §19 row 1 called the band an interim standing in for flows | restore two branches in `te_mon_target_min` / `_max` |
| **Q4** | "On gold" is **one trigger, `te_mon_is_on_gold`** = the law ∧ not suspended, and every peg test goes through it (the metallic anchor, peg defence, gold flows, the 0–15 ceiling, the mandate button). Suspension is a **month counter** (`te_peg_suspended_months`), on the dollarisation precedent (P9); the timed modifiers carry only the prices, and script never reads `has_modifier` on them | "acts as fiat without the law change" (§12.3) needs the law-derived regime overridden, and a missed raw `law_gold_standard` test is silent | grep the monetary files for the raw law test — the survivors are deliberate (regime code, `te_mon_has_dial`, the dashboard's gold-rows gate, the law-gone reset in step 10) |
| **Q4** | A suspended country gets fiat's **range, anchor, credibility and mandates** — and **not** OMO or monetisation | §12.3 says "free dial, inflation-constrained", and both tools are gated on the fiat/digital *laws* (the OMO bool, `te_mon_can_monetise`); a five-year emergency is not a licence to print | add `country_can_create_unbacked_money_bool` to `te_mon_peg_suspension` |
| **Q5** | **`reserve_shortfall_pp`** (§6 names it and defines it nowhere) = `4 × max(0, 0.5 − scaled_gold_reserves)`, capped at 2, and **2 outright while in debt**. Peg defence rounds its target **up to a tenth** with its own hysteresis (move when below the formula; come down only when > 0.35 above it) instead of the shared round-to-nearest-integer ± 0.75 — *revised after the first playtest from a whole point, see below* | an integer target under a fractional world rate sits *below* it half the time under round-to-nearest, and a peg defender parked below the world rate bleeds gold by construction — §19's "AI on peg defence survives a 2pp rise" fails on rounding alone | the 2 and the 0.5 in `te_mon_peg_shortfall_pp`; owner decision **J** |
| **Q6 — superseded by the hybrid model** | "In debt" (§12.3) is **`scaled_debt > 0`**. Inflows also stop while in debt, not only outflows | gold arriving into a debt pays it down, and could then never be asked back because outflows stop in debt — free money through the back door | one trigger line |
| **Q7** | Hot money leaves at 2× the ordinary speed **with a floor of a 0.5pp gap**, and a pending exit that *cannot* be paid hits peg confidence at that doubled, floored rate | §12.2 has the balance leave "when the gap falls to ≤ 0", but 2 × a zero outflow is zero — and peg defence parks everybody at a gap of zero. The confidence half is what makes spending borrowed gold dangerous rather than free | `te_mon_gold_hot_exit_gap_floor` |
| **Q8 — superseded by the hybrid model** | The hot-money **balance is capped at one reserve limit** (inflows stop when it is reached, whatever the vault holds) | §12.2's own argument is that the reserve cap "would only stop a hoarder"; an unbounded balance leaves 12% of GDP a year for a player who spends it. Owner decision **I** | `te_mon_gold_inflow_room` |
| **Q9 — revised: the payout is out of the vault, never the treasury** | A country that stops being on gold **altogether** (law changed, bank gone, command economy, dollarised) pays its whole hot-money balance out **at once, debt or no debt**, and its confidence resets to 100. A **suspension freezes** both instead | "pull gold in, then enact fiat" is otherwise §20 risk 7 by another door; suspending convertibility *is* refusing to pay gold out | the `else` branch of `te_monetary_update_gold` |
| **Q10** | Confidence **seeds at 100**, heals **+1 a month** while not under pressure *and the gap is ≥ 0 with no borrowed gold pending* (otherwise it holds — revised after the first playtest, where a −3 gap with a healthy vault gained confidence while it drained), the four §12.3 terms apply independently while under pressure (`+2` needs only gap ≥ 0 and no pending hot-money exit — "reserves are rebuilding" cannot be tested and is never true in debt), and resumption after a suspension restarts it at 50. The crisis has a 24-month cooldown set by step 10, the same shape as the hyperinflation crisis | §12.3 gives no start value, no recovery and no cooldown; without recovery one episode scars a country for the campaign | four constants |
| **Q11** | §9.1's **gold-supply term stays deferred** (`(proposed)`, owner undecided — P2), and with it "mine output as a positive input to `te_peg_confidence`" | not in §19 row 3 | — |
| **Q12** | Devalue's "expected inflation +3" is delivered as **+3pp of inflation *pressure*, decaying over two years** (`te_mon_peg_devaluation_pressure`) | under gold, expectations are pinned at 0 and step 6 re-pins them every pulse, so a write to `te_inflation_expected` is gone in a month | one modifier |
| **Q12** | Devalue's revaluation is **15% of the reserve limit** (3% of GDP), its export boost `±0.15` for five decaying years, and its infamy / GP relations are the old button's exact **+1 / −3**, restated rather than shared | §12.3 sizes none of them; the button's effect also switches on a JE tool, which this is not | the modifier and one script value |
| **Q13** | `te_peg.1` **writes `te_peg_confidence` and two clocks** — the phase-3 entry on the variable contract's list of documented outside writers | §12.3 defines Defend and Devalue *as* a jump in confidence, exactly as §9.2 defines its escapes as resets | — |

#### Deferred (phase 3's additions)

- The **gold-supply term** and mine output into confidence (Q11).
- **History**: no chart or marker for the world rate, the flow or confidence.
- A **confidence bar** widget — §3 asks for a bar; the row prints the figure and a word.
- Nothing removes an active suspension's modifiers if the gold *law* goes mid-suspension; the
  counter is cleared (step 10), the +2pp / lost-credibility modifiers run out their clocks.

#### Known roughnesses (phase 3)

1. **A suspended gold standard's law tooltip still advertises the credibility bonus**, with
   `te_mon_peg_credibility_lost` cancelling it line for line in the modifier list.
2. **The flow reads one month late in inflation** (step 10 runs after step 6) — the same lag
   ruling P5 accepts for the stance gap.
3. **Defend's floor is `ceiling(world + 4)`**, so it can be up to a point more than +4.
4. **A peg defender's target can sit up to 0.35 above its formula** before it steps down
   (Q5's hysteresis) — small standing inflows, which become hot money and pay the carry.
5. **`te_mon_peg_state` reads "Trusted" for a country that has never been under pressure even
   with an empty vault the month it empties** — confidence is a stock, and says so a month
   or two later.
6. **The Defend clock and a delegated peg-defence bank are redundant but harmless** — the
   clamp raises the target the mandate set.
7. **Command economies on the gold law** take step 10's off-gold branch (no dial): hot money
   is paid out the month they go planned.

#### The bank's own reserve — the hybrid model (owner decision, 2026-09-20)

§12.2 moves gold with `add_treasury`, and the first version did. Playing it raised three
things at once: reserves changed with nothing in the budget to say why; a healthy *treasury*
made the peg unbreakable however reckless the rate; and four rulings existed only to stop a
player **spending** borrowed gold. The owner's call was to split the stock:

- **`te_bank_gold` is the central bank's own vault**, measured against the engine's
  `gold_reserves_limit` (so it grows with the economy and thins out if never topped up).
  Gold flows move it and **nothing else**; the peg-defence shortfall, the pressure test and
  peg confidence all read it. It is seeded, without touching the treasury, the first pulse a
  country has gold flows: the share of the limit its treasury holds, floor **0.5** — where the
  shortfall is zero, so a fresh gold standard asks for exactly the world rate and §7.4's
  Britain figure is back to the phase-1 number. Losing the gold *law* un-seeds it.
- **The fiscal link is `Recapitalise the Bank`** (op 13; `te_mon_effect_recapitalise_bank`):
  a tenth of the limit from treasury to vault, cash in hand only, **one way** — a reserve the
  government could draw on is a second wallet. The AI does the same inside step 10, a step a
  month, when its vault is under a quarter and its treasury over half full.
- **The carry is the only thing the treasury sees**, as the scaled budget expense
  `te_mon_gold_carry_expense` (`country_expenses_add`, weekly) — a fourth scaled-modifier
  site on step 6d's exact shape. It is ordinary interest, so the deficit readers counting it
  is correct.
- **Devalue** revalues the vault (+15% of its limit) instead of paying the treasury.

**The vault's limit is `0.2 × GDP`, not the engine's `gold_reserves_limit`** (one revision used the latter). The engine's figure carries every `country_gold_reserve_limit_mult`, and the largest source of those is `institution_national_bank` itself (+20% a level) — so a country that invested in its central bank watched the limit outrun the gold in the vault and was pushed toward the shortfall by its own spending.

**What it retired:** Q6's "no inflow in debt", Q8's hot-money cap, Q9's payout *from the
treasury* (borrowed gold now goes home out of the vault), the capitalised carry, the
"outflow never exceeds the treasury" cap — and **owner decision J**: the shortfall no longer
treats treasury debt as an empty vault, so an indebted AI with a sound bank sits on the world
rate. `te_mon_peg_under_pressure` is now the vault under a tenth of its limit and nothing
else; confidence's `−2 at scaled_debt ≥ 0.5` term stays, as a statement about the sovereign.
**What it costs:** the peg no longer bleeds the budget directly — §12.2's "a 2pp gap costs a
quarter of revenue" sizing argument is moot — so the peg bites through confidence, the
crisis, the carry and whatever the player chooses to recapitalise. §12.2's `add_treasury`
paragraph and §17 check 11 are superseded by this section.

#### Balance pass on the structural tier (owner, 2026-09-20)

Three sources of `country_credit_standing_add` were resized together, because between them they
put every recognised country on the floor by the late game and did nothing at all for a great
power after era 3:

- **`institution_national_bank` −0.3 → −0.15 a level** — §7.5 judged it against vanilla's cap of
  five levels; this mod's is nine.
- **The five mod techs −1.8 → −1.35 in total, and moved** off `containerization`,
  `social_justice_movements`, `decline_of_organized_religion` and `mind_backups` (inherited, in
  place, from the old `country_loan_interest_rate_mult` sites) onto techs that are about finance
  or the machinery of it. `artificial_intelligence` was considered for the last and rejected as
  already the strongest tech in the mod; `machine_learning` carries it instead.
- **The last two lower the FLOOR by 0.1pp each**, so late finance tech is worth something to a
  country already on it — which is every great power from about era 3.
- **The access ladder's last 1.5 points are back-loaded** (0.25 / 0.5 / 0.75). The first two steps
  are pinned by §7.4: what remains after them is what a tier-1 country carries in 1836.

Net: late discounts total −2.7 (−1.35 techs, −1.35 bank) rather than −4.5, so an insignificant
power (+3 rank) no longer reaches the floor on tech and the bank alone, and §7.4's late-game GP row
reads `0.5 − 0.5 − 1.35 − 1.35 = −2.7 → floor 0.3` rather than `−3.3 → floor 0.5`.

#### First playtest — owner, 2026-09-20 (Britain and France, 1836, game 1.14.3)

Read from the dashboard and `te_debug_monetary.8`; `debug.log` / `error.log` carried nothing
monetary. **Confirmed:** items **40** (`add_treasury` moves the treasury by exactly the printed
flow — 1.333 × 54,139 = 72,178), **41**'s ceiling half (gold reads 0 / 15, a suspended-free
France 0 / 25; the Defend floor is still unwalked), **42** (accumulators 117.298 / 27.069 =
4.333 with Britain manual, 0 / 0 on peg defence), **39a** (carry 647 = 179,213 × 4.333 ÷ 1200),
**39b** (Britain's own copy 3.000 against a global 4.333) and the day-one half of **36**.
Gold rows show for Britain and not for France.

**§17 check 7, answered: country monthly pulses are STAGGERED, not all on the 1st.** Britain's
step-10 payment read reserves of 3,456,393 → 3,290,579 (exactly the −165,813 flow), and by
31 January the treasury stood three weekly budget ticks below that — so Britain's pulse fired
around the **13th**. France's copy of the world rate lagging the global by a month is the same
fact seen from the other side: each country's pulse falls on its own day, before or after the
global `on_monthly_pulse`, so a consumer sees the world rate up to a month late. That is the
lag ruling Q1 already tolerates. (An earlier revision of this note concluded "country pulse
runs before the global one"; that was an over-reading of one data point.) **Practical
consequence for every check in this document: compare across a whole month, never across the
31st → 1st.** `add_treasury` was confirmed landing, and visible to a read in the same block.

**What the playtest changed:** ruling **Q5** (peg defence now rounds up to a *tenth* — Britain's
quarter-full vault asked for 3.46 and the whole-point rule gave it 4, a standing point of gap
and carry on gold it had no use for); the rate-target stepper gained **ctrl-click = 0.1** and
**shift-click = to the limit** (ops 9–12), so a target is no longer always an integer; *Borrowed
Gold* and *Interest on It* became dashboard rows rather than tooltip lines; the block gained
five sub-headings; the label column went 160 → 200 with Delegate / Take Control moved to a row
of their own.

#### IN-GAME VERIFICATION CHECKLIST (phase 3)

Continues the numbering. 36–39 are §19 row 3's four exit criteria — `te_debug_monetary.8`'s
header says how to stage each; 40–42 can invalidate a mechanism; 43–47 are numbers and UI.

36. **World rate = World Reference Rate in 1836, and stays there** under observation until a
    great power takes a discretionary dial. If it moves on its own, some great power is
    passing `te_mon_rate_is_discretionary` that should not — `.8` prints both accumulators.
37. **A world-rate rise drains a small gold country.** `.8` option a, as a small gold country
    on a manual target: gap −2, *Gold Flow* ≈ −0.4% of GDP a month, the treasury falling by
    the same figure, then (under a tenth of the reserve limit) the flow stops and *Peg
    Confidence* falls ~6 a month until `te_peg.1` fires at 20.
38. **AI on peg defence survives +2pp.** Same option, observer mode, two years: targets step
    up within a month, and no `te_peg.1` for a tag that was out of debt at the start.
39a. **The carry is charged, and it capitalises.** With a borrowed balance, the *Gold Flow*
    tooltip's interest line reads balance × policy rate ÷ 1200 and the treasury falls by it each
    month beyond the flow; in debt, the balance grows by it instead.
39b. **The hegemon is constrained.** As a player Britain on a manual target in 1836, *World
    Rate* reads 3.0 whatever Britain's own rate is, the gap is non-zero, and gold moves; as
    France, *World Rate* reads Britain's rate.
39c. **Dollarised pin:** a dollarised country's *Expected Inflation* reads 2.0 every month.
39. **World + 5 yields no lasting gain.** Inflows stop when *borrowed gold* reaches one
    reserve limit even if everything was spent; on dropping the target the balance leaves at
    twice the speed; if it cannot be paid, confidence collapses. Judge the whole run on
    treasury **and** the downturn it cost (owner decision I).
40. **`add_treasury` with a script value that reads a variable** (`te_mon_gold_flow_signed`)
    — every existing use in the mod passes a constant-shaped value. If the treasury does not
    move while *Gold Flow* reads non-zero, that is the cause. Also §17 check 11: an inflow
    near the reserve limit — does the engine diminish it? (`te_mon_gold_inflow_room` caps at
    the limit, so it should never be asked to.)
41. **`value = X` inside an `if` in a script value resets the running total**
    (`te_mon_target_min`'s Defend branch, `te_mon_target_max`'s gold branch). Vanilla does it
    (`ep2_japan_values.txt`); if it *adds* instead, gold's ceiling reads 40 and the stepper
    tooltip shows it at once.
42. **Global-variable arithmetic**: `change_global_variable … divide = global_var:…` and
    `add = <script value>` evaluated in the iterated country's scope inside `every_country`.
    `.8` prints the accumulators; with one discretionary GP the denominator is its GDP in
    millions.
43. **Suspension really is fiat**: *Expected Inflation* unpins from 0 within a few months, the
    target stepper reaches 25, the Peg Defence button disappears, the gold rows stay with
    *Gold Flow* at 0 and the word "Convertibility suspended"; after 60 months confidence is 50.
44. **Defend**: the stepper's minus greys out at `ceiling(world + 4)` with
    `banking_mon_tt_peg_defend_floor`, for 12 months, for a delegated bank too.
45. **Leaving gold pays the hot money out at once** — enact fiat with a balance; the treasury
    drops by it on the next pulse, into debt if need be.
46. **The price–specie term**: a sustained +2 gap shows ~+2.4pp of pressure in
    `te_debug_monetary.1` and a gold country's inflation climbing toward ~+1.2.
46a. **The vault (hybrid model).** On load, *Bank's Gold Reserve* reads at least 50% of its limit
    and the treasury does not move with *Gold Flow* any more; the vault does. *Recapitalise the
    Bank* debits the treasury and credits the vault by the same figure, greys out with one cause
    line when the cash is not there, and is never offered on credit. With borrowed gold in the
    vault, the budget shows an **Interest on Borrowed Gold** expense of about
    balance × policy rate ÷ 5200 a week. **A save made under the first version carries its old
    hot-money balance into the new vault** and goes on paying the carry on it until the gap is
    ≤ 0 — expected, not a bug.
46c. **Modifiers on the journal entry.** As Britain, the country's modifier list no longer shows the
    inflation band (or stance politics, wage dividend, monetisation, gold carry); the banking
    entry's own modifier list does, and their effects still reach the country — the budget still
    shows *Interest on Borrowed Gold*, the band's IG rows still apply. **The scaled ones are the
    risk:** `multiplier = root.var:X` on a JE modifier is the documented form but new to this
    system — a carry line of £1 a week, or minting worth a pound, means the multiplier fell back
    to 1. A country with no banking entry (any bankless tag) still carries its band on the
    country. Build a first stock exchange as a small country and the modifiers should move to
    the new entry on the next pulse with nothing doubled.
46d. **Bars at the top.** Four bars above *Current Conditions* and none at the bottom of the
    banking entry; every OTHER journal entry with scripted bars still shows them where it always
    did (the `journal_entry.gui` override changes one `visible` line). The stance bar's marker
    sits left when tight. A save from before this adds the fourth bar to a live entry — if
    `debug.log` complains about `banking_policy_stance_bar`, that is why.
46b. **Script values on the left of a comparison** (`te_mon_bank_gold_scaled < 0.25`,
    `te_mon_bank_recap_amount > 0`). Vanilla ships the form (`raiding_income > 0`,
    `state_infrastructure_balance < 0`), but this system had not used it before: if
    `debug.log` shows a parse error in `te_monetary_triggers.txt`, that is where to look, and the
    tell in play is a recapitalise button that is permanently grey.
47. **Formatting**: `|+=1` on the gap (*Gold Flow* uses `@money!` with `|D+`, which the mod
    already ships);
    `GetGlobalVariable('te_world_rate_debug_offset')` rendering blank, not an error, when
    unset.

---

### 0.6 The narrow commodity dial — 2026-09-21 (owner asked for the freedom; the shape is proposed)

Closes §5.4's standing open question ("France 1836 has a national bank on commodity
(bimetallic) money, and the Banque de France did set a discount rate… If that feels wrong
in play, give commodity money + national bank a narrow dial (world rate ±1pp)").
**Commodity money with a national bank holds a dial restricted to a band around the world
rate — one point under it, three over** — and commodity money *without* one still has no
dial at all.

> **Status of this section.** The owner's instruction was only "allow some freedom for
> commodity money to set rates". Everything below — R1–R7 and the band's shape — is
> implementation judgement and **open to revision**, not a recorded owner decision. The first
> draft took §5.4's "±1pp" literally (a symmetric three-setting dial); a same-day review
> kept R1 and R3–R6 and **changed R2**, for the two reasons given in its row. A later pass
> (2026-09-21, from a live game — issues #351 and #352) **half-reversed R5** and added
> **R7**: the band disciplines the *rate*, and a metallic regime is supposed to discipline
> the *price level*, which needed a quantity channel of its own.

| # | Ruling | Why | Cost if wrong |
|---|---|---|---|
| **R1** | `law_commodity_money` joins `te_mon_has_dial`'s regime `OR`. The national-bank line already in that trigger is the whole of "only with a bank" | the Banque de France, the Bank of Prussia and the Second Bank all set discount rates on metallic currency; "no dial until you enact gold" was the one rung of the ladder with no player decision on it | one law line |
| **R2** | The band is **lopsided: `centre − 1` to `centre + 3`** (`te_mon_commodity_band_margin_down` / `_up`), five whole settings. `centre` is `var:te_mon_commodity_centre` — the world rate rounded to a point, kept by step 0 and **re-rounded only once the world rate is 0.75 away from it** (the delegated target's hysteresis) | **Realism:** what metal forbids is *cheap* money — a discount rate under the world's sends coin abroad. Dear money was always available and was the period's panic tool: the Banque de France held 4% for a generation, then 5–6% in 1847 and up to 10% in 1857. **Fun:** at ±1 the dial had no decision in it — the lenders' floor eats a cut and +1 is too weak a brake to be worth its interest, so "sit at −1 forever" dominated. At +3 the stance gap reaches *very tight* (≈ −0.4 momentum, −2.3 bubble a month — the old rate-hike button and a bit), paid for by three points on the whole debt. **Hysteresis:** a bare `round(world)` flips the band a point whenever the world rate hovers at x.5, and each upward flip silently clamps a floor-sitting target that the flip back does not restore | two constants, one stored centre, two `else_if` branches in `te_mon_target_min` / `_max` |
| **R3** | The floor is clamped at **0**, not at `country_policy_rate_floor_add` | coin can be hoarded, so the zero lower bound `law_digital_currency` buys its way past applies with full force here; and nothing grants a floor modifier on a rung that is mutually exclusive with digital anyway | one `min = 0` |
| **R4** | A narrow dial is **not discretionary** for §12.1: `te_mon_rate_is_discretionary` gains `te_mon_has_narrow_dial = no`, so these countries stay out of the world-rate average | a band measured *from* the world rate whose midpoint helps *set* the world rate is the same circularity that keeps a peg defender out — see the rewritten §12.1 paragraph | one trigger line |
| **R5** | ~~**No new discipline mechanism.** No specie flows, no convertibility crisis, no reserve. The band *is* the constraint~~ — **half-reversed by R7 below (2026-09-21, issue #351).** No reserve and no convertibility crisis, still; but a price-specie *pressure* term, yes | §12.2's machinery is built on a gold-standard vault this regime does not have in the model; inventing a second, thinner version of it to police a two-point band is cost with no decision in it. **What that argument missed:** the band constrains the *rate*, and the thing a metallic regime is supposed to constrain is the *price level*. A rate bound says nothing about quantity, so nothing in the model stopped a commodity country running a standing 4% core | the band would have to be replaced by flows, which is a phase of its own |
| **R6** | Commodity money keeps **everything else it had**: metallic anchor (expectations pinned at 0, credibility *c* = 1, the regime pull toward 0), **no** OMO, **no** monetisation, the 1pp bankless spread only while bankless | the dial is a discount rate, not a monetary policy — none of the arguments for pinning expectations or forbidding unbacked money turns on whether a rate is chosen | the two on-action law lists and `te_mon_can_monetise`, all unchanged |
| **R7** | **The quantity channel, added 2026-09-21 (issue #351), superseding half of R5.** `te_mon_pressure_commodity_specie`: a commodity-money country carries `−2pp` of §9.1 inflation pressure for every pp its core inflation runs above the world's *beyond the first*, clamped at `−6`. The input is phase 4's `te_mon_fx_term_inflation` — the price-level half of the overvaluation the FX layer already computes — normalised back out of `te_mon_fx_inflation_weight`; the *rate* half (`te_mon_fx_term_rate`) is left out on `te_mon_fx_overvaluation_for_peg`'s precedent, because that is capital flight, not a price gap. One-sided, on `te_mon_fx_overvaluation_value`'s own `min = 0`. Gated on the **law**, so a commodity country without a bank is disciplined too | R5 left the regime with a *rate* bound and no *quantity* channel. The regime pull is a proportion, not an anchor: with expectations pinned at 0 it makes the fixed point `core = X − core`, so hard money **halved** a standing pressure sum instead of holding the price level, and doubling the other pressures doubled the inflation. A live game found a commodity country stable at 4% core / 6.1% headline with its dial pinned at the band ceiling. Historically, under convertible coin the price level is *internationally* determined and the enforcement is specie **leaving**; localized metallic inflation came from debasement, a world metal-supply shock, a transitory goods shock (cost-push, which already mean-reverts) or suspended convertibility — not from a stable domestic pressure sum. It also gives §15.6's dead row a job: `te_mon_overvaluation` was display-only under commodity money | three §21 constants, one term in `te_mon_pressure_total`. **The tolerance is the floor:** the equilibrium solves `core × (2 + per_pp) = X + per_pp × (π_w + tolerance)`, so no value of `per_pp` holds a commodity country below `world inflation + tolerance` — retune the tolerance, not the slope |

**What the dial actually does, and what it does not.** The lenders' floor (§10) is
`max(policy, era_base + expected)`, and metallic expectations are pinned at 0 — so a
commodity bank cutting to `world−1` barely moves the rate its treasury pays, because
`era_base` catches the cut. **Easing** therefore lands almost entirely in the **stimulus
channel** (§8): about a point of loose stance gap — a real if modest lean against a slump —
with the §9.1 loose-money pressure that comes with it, against a regime pull dragging core
inflation back to zero (it settles near +0.2pp; the cost of sitting loose is the bubble, not
prices). **Tightening** is the opposite trade: every point over `era_base` is a point on the
whole debt, bought for a brake on momentum and bubble pressure that at `+3` is as strong as
the deleted rate-hike tool. That is the intended reading of "limited control" — enough to
lean against a season and to break a fever, not enough to run a policy.

**The `+3` brake is a *nominal* margin against a *real* stance (issue #352, decided
2026-09-21).** The band is whole points off the **world rate**; the stance gap is
`policy − headline − neutral`. Metal pins *expectations* at 0, not *inflation*, so at any
material inflation the two part company: at a 3.0 world rate and 6.1% headline the whole
five-setting dial maps to a real rate of −4.1% to −0.1% and the *top* setting reads **Very
Loose** — there is no tightening setting on it, and the panic brake described above does not
exist. Neither escape works either: step 2b re-clamps a Price Stability mandate's formula
back into the band on the same pulse, and open-market operations are fiat/digital-only.
**Resolution: leave the band alone and fix it upstream (R7).** Centring the band on
`world + headline` would hand a coin economy a fiat-sized nominal dial exactly when prices
move, which is the opposite of what the regime is for; a coin economy inside a 6% inflation
*should* be nearly powerless. What R7 changes is that it should not be in one — with the
price-specie term holding standing core near the world's, the brake is there whenever the
band is what stands between the country and a bubble. The margin's own comment in
`te_mon_commodity_band_margin_up` now states the condition it assumes.

**Known roughness — a standing tight bias is possible.** The band is measured from the
*world* rate and the stance from the country's *own* neutral rate. A slow-growing commodity
bank facing a world rate a point and a half above its neutral has a floor that is already
tight: the "hidden penalty nobody chose" §8 warns about, arriving here as a cost of banking
on metal while the hegemon runs dear money. It is the same exception §8 already grants the
peg defender, it is historically the right complaint, and the way out is the ladder's next
rung. A bankless commodity country keeps gap 0.

**Two consequences worth naming.** (1) Commodity-money banks now also get **delegation and
the price-stability / growth mandates**, because both hang off `te_mon_has_dial`; peg
defence stays gold-only, so nothing there needed a gate. (2) A commodity-money AI is
therefore delegated like every other AI and will sit wherever its mandate lands inside the
band — in practice `world` or `world+1` at the 1836 start, which is what it paid before.
(3) **Stance politics (§13) now reach commodity banks** too, since they hang off the same
gate: a bank held at the top of its band for a year angers the debtor groups exactly as a
fiat one would. Intended — it is the political price of the panic brake.

**Save compatibility.** Step 0 seeds `te_policy_rate_target` to `round(era_base)` = 3 and
`te_mon_commodity_centre` to `round(world)`, and step 2b clamps the target into the band on
the first pulse, so a France 1836 save picks up a legal
target without a jump; `te_policy_rate` drifts off the old derived `world + 1` at the
ordinary third of a point a month. Nothing is removed and no variable changes meaning.

### 0.7 Phase 4 as shipped — rulings, deviations and open checks

Phase 4 (§19 row 4) was implemented in the working tree on 2026-09-21, on top of §0.6:
`te_fx_shadow` for everyone and `te_fx_index` by regime, world inflation with the own share
excluded, the overvaluation drain on a gold peg, `te_fx_weak` / `te_fx_strong`, imported
inflation inside cost-push, the FX premium, `controls_damp` and capital-controls fatigue, the
dashboard rows, a seventh history chart, the §18.2 deletion with its save migration, the FX
events re-pointed at `te_fx_shock`, and a console harness (`te_debug_monetary.9`). **Nothing
below has been seen in a running game**; phases 1–3's open checks are inherited unchanged.
Both reloads (`mod_only + audits_only`) came back with no parse failures and no audit
findings. File inventory and the architectural rules: `mod_systems.md` § Banking Cycle →
**Monetary Policy (phase 4)**.

#### Owner decisions to review (phase 4)

| # | Ruling | Why | Cost to reverse |
|---|---|---|---|
| **F1** | **A country without a dial earns no carry**: `te_mon_fx_term_rate` is 0 unless `te_mon_has_dial`. §15.2 left this "(proposed)" as "the rate term is pinned near +1 (the bankless spread)" | a derived rate is world + expected + 1, so its real gap is a constant +1: every bankless floater would sit four points strong for ever — a −5% export edge nobody chose, the exact standing penalty §8 refuses to deliver through the stance. The spread is a risk charge, not a return anyone crosses a border for. It also makes §19's "the 1836 world sits at par and stays there" true for the bankless majority by construction rather than by luck | delete the `te_mon_has_dial` line in `te_mon_fx_term_rate` |
| **F2** | **World inflation averages each great power's FX read, not raw `te_inflation_expected`**: `te_mon_fx_inflation_read` is realised core for a metallic member, expected otherwise — the same substitution §15.2 makes for the metallic *shadow* | §15.1 says "GDP-weighted mean of `te_inflation_expected`". In an all-metal world that is identically 0 (Q12 pins it), while every member's own read is core: a gold rush that lifts everyone's core by 2pp would make every peg 4 points "overvalued" against a world that was inflating with it. Like is now compared with like, and §19's "no overvaluation drain at the 1836 start" holds under a common shock too. Command economies are left out of the average (their inflation is administered to 0) | swap `te_mon_world_inflation_weighted`'s base for `var:te_inflation_expected` |
| **F3** | **`controls_damp` applies to both signs of the gold gap**, after the ±5 clamp | §15.4 says it multiplies "§12.2's gold-flow gap". Damping only outflows would make controls a way to bank a high rate's inflow at full speed while being protected on the way out; money that cannot leave does not arrive either | an `if` on the sign in `te_mon_gold_gap_value` |
| **F4** | **The overvaluation drain ignores the vault, and ignores the part of overvaluation a low rate caused.** The rate-gap drain only bites while `te_mon_peg_under_pressure` (vault under its floor); this one bites whenever `te_mon_fx_overvaluation_for_peg` = `max(0, overvaluation + min(0, rate term))` is > 5, and blocks the +1 heal | §15.2 asks for a term "beside the rate-gap drain (adding to it, not replacing it)" that counts as pressure for Q10, and §19 asks that "a gold country that inflates 5pp above the world for three years loses its peg through the overvaluation term" — which a full vault would otherwise prevent for ever (5pp → shadow ≈ 91 at two years → ≈ 2 confidence a month, 100 → 20 in roughly forty months). **But the raw shadow also falls on a low *rate*, which gold already prices through the vault**: uncorrected, a gold player at world − 2 with a full vault would bleed 1.5 confidence a month where phase 3 bled none, and row 3's "AI on peg defence survives a 2pp world-rate rise" would turn marginal (drift lag → shadow ≈ 96). So the carry term's *negative* contribution is taken back out before the test; a rate *above* the world's still props the parity, which is how a dear-money defence should work. **The riskiest ruling here — it touches every gold country** | the alternative is one line: gate the new `if` in step 10 on `te_mon_peg_under_pressure = yes` (then overvaluation only ever *accelerates* a run that gold flows started, and §19's three-year inflation test cannot pass) |
| **F5** | **The crash option *Suspend convertibility* sends a −13 shock** in place of its modifier's deleted `state_export_advantage_mult = −0.10` | §15.5 says "field removed — the float now produces the export effect, with the right sign", but that crash option does not by itself float anything (only §12.3's *Suspend* does). A payments freeze weakening the currency by ~5 points is the smallest thing that makes the sentence true; a metallic country sees it only as overvaluation | delete one `custom_tooltip` line in `minor_events_timelineextended.6` |
| **F6** | **`monpol_currency_devaluation` is three sites, not a pair** — all three law-event options get the −13 shock | §15.5 counted two; `events/extra_law_events.txt` has three | — |
| **F7** | **A metallic index snaps to par on the first pulse under metal**, whatever it was as a float, and a country *leaving* metal jumps straight to its shadow | §15.2's table read literally. Enacting a standard is choosing a parity; abandoning one with a shadow at 85 is 1931 sterling. The jump is an imported-inflation event of up to `0.15 × gap × openness` pp, inside the ±6 clamp | blend the index toward the shadow instead of setting it |
| **F8** | **A scaled modifier at zero is removed, not applied at zero**, and re-applied only when its multiplier moves by half an index point (1/12 step for fatigue) | §15.3 says "always both, a zero multiplier on the inactive one"; an empty line in the modifier list is noise, and step 9's threshold recipe already exists for the rate paid. Cost: up to 0.6% of trade edge of staleness | `STEP` parameters in `te_monetary_apply_fx_modifiers` |
| **F9** | **Tech replacements (§15.6) not designed.** `keynesian_economics` and `international_exchange_standards` each simply lose one tool-unlock bool | left open by §15.6; both techs keep their other unlocks | — |

#### Known roughnesses (phase 4)

- **Devalue now prices its import cost twice, mildly.** `te_mon_peg_devaluation_pressure`
  (+3pp, Q12) was phase 3's stand-in for dearer imports; the index drop to 88 now also feeds
  `te_fx_imported` (≈ +1.8pp × openness, fading over three years, inside the ±6 clamp). Left
  as is: the first acts on core, the second on headline, and a devaluation *should* hurt. If
  playtesting finds it heavy, halve the modifier rather than exempting the index.
- **The Gap to World Rate row shows the damped gap** under capital controls, because
  `te_gold_flow_gap` is what step 10 acts on. True to the mechanics, but the row's name
  promises arithmetic the player can no longer check by eye; the controls tooltip says why.
- **Commodity-money overvaluation is display-only** (§15.6, unchanged): no `te_peg_confidence`
  to drain. With §0.6's narrow dial those banks now show a meaningful shadow.
- **The button count in `journal_entry_systems.md`** was reduced by four on the assumption
  that the old figure was right; §22 already lists that doc's counts as drifting.
- **`te_fx_strong` on a creditor hegemon is a standing export penalty** — intended (the
  reverse of the weak edge), but it is the first time the mod taxes *tight* money through
  trade, and §19's extended §10 invariant only tests the loose side.

#### IN-GAME VERIFICATION CHECKLIST (phase 4)

Continues the numbering of §0.5. Harness: `event te_debug_monetary.9` (description prints
every figure; options a / b / c stage the shocks), beside `.5` (fixed manual target) and `.8`
(gold).

- **P4-1. §17 check 13** — do `state_export_advantage_mult` / `state_import_advantage_mult`
  on a *journal-entry-scoped scaled* modifier reach the states? Read a state's trade tooltip
  with `te_fx_weak` applied. If not, the fallback is `te_mon_mod_home = 0` for these two.
- **P4-2. §17 check 20** — does `market_trade_reliance = { value > 0.3 }` evaluate without a
  log error in market scope, and do the three openness bands appear in `.9`'s read-out
  (0.6 / 1.0 / 1.5)? It has no vanilla script use.
- **P4-3.** The 1836 world sits at par and stays there: every metallic tag prints
  *Par (convertible)*, bankless floaters hold ≈ 100 (F1), and no gold country shows an
  overvaluation drain at start.
- **P4-4.** A fiat harness tag held 2pp loose settles at **92–94** within two years.
- **P4-5.** A gold country 5pp over world inflation for three years loses its peg through the
  overvaluation term (F4's projection: about forty months from 100).
- **P4-6.** A gold country under controls holding world − 4 drains like world − 1; the same
  country's fatigue reaches −5 / −5 / −10% after ten peacetime years and is frozen by a war.
- **P4-7.** Harness level shock −20 under price stability: headline back within 1pp of its
  pre-shock path in four years (§20 risk 9 converges); the history chart shows no sawtooth.
- **P4-8.** Event shock −26 troughs near −10 at about eleven months; two in a row respect the
  ±40 clamp.
- **P4-9.** *Devalue* in `te_peg.1`: index 88 at once, ≈ 94 at 21 months, par at 60; the
  option tooltip's ±15% matches the trade tooltip.
- **P4-10.** A pre-phase-4 save holding `banking_fx_devaluation` loads with index 80, no
  modifier, no error-log line; likewise 120 for `banking_fx_support`.
- **P4-11.** 50-year observer run: no floating AI pinned at 50 or 150 outside the
  hyperinflation band (a failure is fixed in §6's mandates, not the FX constants); median
  fiat inflation still 1–4% with imported inflation on; AI still uses its remaining tools and
  does not sit on capital controls in peacetime.
- **P4-12.** The extended §10 invariant: a fiat tag at the loose clamp for 20 years ends worse
  on treasury, SoL and radicals than a neutral one *with the trade edge on*. If it fails,
  halve `te_fx_weak` / `te_fx_strong`'s per-point value before touching the formula.
- **P4-13 (§0.6 R7, issue #351).** A commodity-money tag carrying the pressure sum that used
  to settle at **4% core / 6.1% headline** now settles near **2.5% core** — comfort band once
  the cost-push mean-reverts — and `te_debug_monetary.1` shows a *Commodity specie* term
  between −2 and −4pp. Closed form, with `X` the rest of the sum at equilibrium:
  `core × (2 + per_pp) = X + per_pp × (π_world + tolerance)`, i.e. X = 4 → 1.5, 6 → 2.0,
  8 → 2.5, 10 → 3.0, 14 → 4.0 (the −6 clamp binds from there), against `X / 2` before.
  A quiet commodity tag — stance near neutral, no deficit, stable phase — should be
  **unchanged**: the term is a dead band below `world inflation + 1`.
- **P4-14 (issue #352).** Confirm the band still reads as intended once P4-13 holds: a
  commodity tag inside its comfort band and a world rate near 3 reaches stance band 5
  (*Very Tight*) at the `+3` setting. The band is nominal and the stance real, so this is a
  check that R7 keeps the precondition, **not** that the dial gained a setting.

### 0.8 Phase 5 as shipped — rulings, deviations and open checks

Phase 5 (§19 rows 5a, 5b, 5c) was implemented on 2026-09-21, on top of §0.7, as three commits
in the order **5a → 5c → 5b** (5c needs only the spine; 5b needs 5a's lender-of-last-resort
event) — each still cuttable. **Nothing below has been seen in a running game, and it is
built on a phase 4 that has not been either** (§0.7): phases 1–4's open checks are inherited
unchanged, and phase 5 leans on phase 4's `te_fx_shadow` / `te_mon_overvaluation` for every
pressure gauge it has. Every reload (`mod_only`, generators on) came back with no parse
failures and no audit findings. File inventory and the architectural rules: `mod_systems.md`
§ Banking Cycle → **Monetary Policy (phase 5)**.

#### Owner decisions to review (phase 5)

| # | Ruling | Why | Cost to reverse |
|---|---|---|---|
| **G1** | **An anchored country keeps its hidden state running**: a new `te_mon_has_stance` (= dial **or** anchored) replaces `te_mon_has_dial` at the three hidden-state gates in the monthly update — the inflation noise walk, the two neutral-rate walks, the stance gap itself | §15A.1 promises "a single edit that propagates to every consumer", and also that an anchored country "keeps its own inflation, neutral rate, stance gap and cycle. This is the whole point". The two conflict: those three gates zero the gap and freeze the walks for anyone without a dial, which would make the imported rate never *wrong* — no stance politics, no 5c liberty-desire lever, nothing for `te_mon_overvaluation` to mean. Other no-dial countries are unchanged (their real gap is a constant and stays 0) | point the three sites back at `te_mon_has_dial` |
| **G2** | **The monthly leg of detection runs the *full* discovery, but only for flagged countries.** §15A.1's three-way split stands (monthly / hooks / yearly scan); `te_mon_arr_scan = 1` marks a country that holds any role — anchored, an anchor, either side of a backstop, a board subject, a member of a bloc with the union group — and step 1c re-runs `te_monetary_discover_arrangements` for those every month. Everyone else runs nothing monthly | the split existed to avoid a treaty walk for ~200 countries a month. The walk is over a country's *own* in-force treaties, and only a few dozen are ever flagged, so the cost is not paid — and "is the stored pair still valid" is answered by the code that found it rather than by a second copy of each kind's rule. The flag seeds to 1, so a save from before phase 5 discovers itself on its first pulse | replace the call in `te_monetary_update_anchor` with per-kind validity tests |
| **G3** | **`te_mon_is_anchored` reads stored state only; validity is step 1c's job.** Discovery hooks dispatch a new **`te_monetary_internal.2`**, not `.1` | validity is "the anchor has a dial", and `te_mon_has_dial` asks `te_mon_is_anchored` of the anchor — testing it inside the trigger makes the two call each other down the chain. Step 1c runs before 1b and 2, so within a pulse the stored pair is always a checked one. `.1` **is the monthly update** and is not idempotent; the discovery is, so hooks may overlap freely. It still needs ROOT = the country (its treaty walk tests `source_country = root`), hence an event at all | — |
| **G4** | **"Re-peg lower" moves the parity, not the shadow**: `te_mon_peg_parity_offset` += half the overvaluation, and an anchored index is *anchor's index − offset* | §15A.2 re-bases the country's shadow upward. Same cut in overvaluation either way, but a moved parity is also an actual devaluation — the trade edge and the imported inflation a negotiated devaluation should carry — and a re-based shadow decays back at 1/12 a month, quietly undoing the option within a year | swap the body of `te_mon_effect_anchor_peg_repeg` |
| **G5** | **Joining re-seeds `te_fx_avg` after the snap; leaving does not re-seed at all** | §15A.1 says re-seed "on any change". Adopting somebody's money is a redenomination, not a price event; but leaving "**is** the devaluation", and imported inflation exists to price exactly that (the reasoning `te_mon_effect_fx_devalue_peg` already gives for §12.3's Devalue) | one call in `te_monetary_anchor_changed` |
| **G6** | **A drawn swap line pays the recipient.** The provider's 0.1%-of-recipient-GDP monthly draw lands in the recipient's treasury | §15A.2 states only the draw. "Under gold a swap line *is* reserve lending" — money that leaves one treasury and arrives nowhere is a tax, not a loan. 1.2% of GDP a year, only while `te_mon_in_external_crisis` | delete the recipient's `add_treasury` |
| **G7** | **Currency boards do not count toward the reserve-currency cut** | "per 5% of world GDP *pegged* to it": a board is imposed, not a vote of confidence, and counted, the East India Company alone would hand Britain the full −0.5 on day one | the `kind < 3` line in `te_monetary_refresh_anchored_gdp` |
| **G8** | **No monetary term lives in an article's `source_modifier` / `target_modifier`, and there are three arrangement modifiers, not two.** `te_mon_arrangement_recipient` and `_provider` carry cyclical points as designed; a third, `te_mon_arrangement_standing`, carries the *structural* ones (the pegger's −0.5, the reserve currency's cut), because one multiplier cannot scale two fields differently. Articles carry prestige only | this **bypasses §17 check 14** rather than answering it (the §0.1 precedent for check 6) | — |
| **G9** | **`state_trade_advantage_mult` does not exist.** An adopter gets `state_export_advantage_mult` and `state_import_advantage_mult` +0.05 each (`te_mon_union_adopter`) | the engine has only per-good `goods_trade_advantage_*`; the export / import pair is what phase 4 already uses | — |
| **G10** | **The union's tier is read through `has_principle`, and "cohesion per adopter" is per member.** The three `power_bloc_*_bool` markers exist for the principle tooltip only; `power_bloc_cohesion_per_member_add = 1` sits on tiers 2–3 | **bypasses §17 check 16** (`has_principle` has vanilla script precedent). And no script can put a modifier on a bloc, so a per-adopter cohesion term cannot be applied; per-member is the nearest static form | — |
| **G11** | **The Question fires on three of §15A.3's four triggers.** Pressure newly applied, criteria newly met and a tier change are one integer signature (`te_mon_union_q_state`); **a change of government in the holdout is not shipped**. `te_mon_union_last_asked` is a countdown (`te_mon_union_ask_cooldown`), not a date | there is no cheap government-change signature, and a date variable buys nothing a countdown does not | — |
| **G12** | **"Panic severity inputs reduced" is one site**: an imported crash's `crash_severity` × 0.8 for a country with an effective backstop (treaty guarantee or tier-3 union) | origin crashes are rolled in generated events (`gen_banking_events.py`); the contagion path is script and is where a foreign guarantor plausibly matters | — |
| **G13** | **The imported rate carries no expected-inflation term** (`anchor's rate + spread`, where a bankless rate is `world + expected + 1`) | the anchor's nominal rate already carries the *anchor's* expectations; that it ignores the borrower's is the cost of the arrangement, and the borrower's stance gap (G1) is the measure of it | one `change_variable` in `te_monetary_set_derived_rate` |
| **G14** | **"Break the peg" withdraws from the whole treaty** | `withdraw` is a treaty effect; an article cannot be dropped alone. The option tooltip says so | — |
| **G15** | **Defend forces controls with a clock, not the banking tool.** `te_mon_emergency_controls_months` = 12, read by a new `te_mon_capital_controls_in_force` that replaced `banking_tool_capital_controls_active` inside `te_mon_controls_damp` and the fatigue counter | a treaty pegger need not hold the banking journal entry the tool lives on. Forced controls therefore damp and fatigue exactly like chosen ones, but carry none of `banking_capital_controls_out`'s other fields | — |
| **G16** | **Numbers that were not in the design**: AI leader presses at influence ≥ 300, cohesion ≥ 60% and fewer refusers than holdouts; AI adopter exits at 30 points of overvaluation; pressure costs 50 influence a holdout; the exit pool hit is 2% of GDP and 5% radicals; refusing costs the leader 5% cohesion and 15 relations; `te_mon_board_wrong_stance` is +0.15 liberty desire; LOLR renege is 5 infamy, −10% prestige and +0.5pp standing for five years; articles cost 25 / 50 / 75 influence | all (proposed) until the harness has been run | the named values in `te_monetary_union_script_values.txt` / `_arrangement_script_values.txt` and `extra_modifiers.txt` |

#### Deferred (phase 5's additions)

- **Grant monetary autonomy** (§15A.4) — named, not designed; unchanged.
- **A named list of holdouts on the leader's dashboard.** Shipped as two counts (holdouts,
  and how many would refuse today), which is what the design wanted the list *for*.
- **The government-change trigger for The Question** (G11).
- **Re-expressing `te_mon_dollarised` as "anchored to the hegemon"** (§15A.5) — recorded, not
  proposed; unchanged.

#### Known roughnesses (phase 5)

- **The exit invariant is untested.** §19 row 5b's "exit must be worse than staying for ≥ 5
  years at 15 points of overvaluation, and better thereafter" is a harness run nobody has
  made. At 15 points an adopter pays +1.0pp (0.5 at tier 3) against the exit's +3pp decaying
  linearly over ten years — so exit is dearer on the premium alone for about 6.7 years (8.3
  at tier 3) before counting the trade edge regained. Plausible; unverified.
- **A provider's cost is as fresh as its last discovery.** Flagged countries discover monthly,
  so in practice a month; a ward's relief, which moves with its debt, is refreshed every pulse
  on the ward's side.
- **A member is charged the exit when the *leader* loses its dial** (law change, command
  economy). §15A.3 says losing the ground is an exit "not silently"; it does not distinguish
  whose fault it was. The likeliest complaint from a playtest.
- **A gold-standard country can sign a `currency_peg`.** It then has no dial, so gold flows
  stop and its vault and hot money freeze as under a suspension; its index is the anchor's.
  Coherent, odd, and cheap to forbid in `te_mon_can_peg_to` if it reads wrongly.
- **The four article keys `*_effects_desc` / `*_article_short_desc` land in
  `te_unused_l_english.yml`**, like every existing article's: `organize_loc.py` cannot see
  engine-constructed keys. The file is loaded, so they render; the detection gap is old.
- **Hooks fire a day late on purpose** (`days = 1`), so the treaty's own state has settled
  before the discovery walks it. Whether `on_entry_into_force` would see the treaty in
  `any_scope_treaty` with no delay is unknown and no longer matters.
- **`scripting_best_practices.md` cites the deleted `banking_effect_cb_fx_swap_lines`** as its
  self-relations example. Stale, harmless.
- **`concept_fx_swap_lines` is kept**, re-written to describe the article.

#### IN-GAME VERIFICATION CHECKLIST (phase 5)

Harness: `event te_debug_monetary.10` — the description prints the whole anchored state;
option a pins a **treaty-less debug kind-1 anchor** on the largest dial economy (the
discovery honours `te_mon_debug_anchor_on`; nothing in play sets it), b releases it, c sets
peg confidence to 25, then "run the discovery" / "run one monthly update". Beside `.8`
(world rate), `.9` (shadow shock) and `.5` (fixed target).

- **P5-1. §17 check 18** — with a debug anchor pinned, does *Anchor's rate (copy)* ever read
  0 or lurch? It may lag the anchor's dashboard by a month; it must never be anything worse.
- **P5-2. §17 check 15** — does a treaty under `non_fulfillment = freeze` still iterate under
  `any_scope_treaty`? No phase-5 article uses `freeze`, so this only matters if a peg is
  bundled with one that does: read kind on `.10` after the freeze.
- **P5-3. §19 5a** — an AI minor pegged to a GP tracks a 2pp anchor hike within two months
  (`.8`, or hike as the anchor) and survives it.
- **P5-4. §19 5a** — the same peg **breaks** under 15 points of *sustained* overvaluation:
  drain 5 a month, 100 → 20 in 16 months. One `.9` shadow shock is not sustained (≈ 50 points
  in total); repeat it, or hold a real inflation differential.
- **P5-5. §19 5a** — a GP's *Backstops Extended* for a minor is < 10% of the minor's
  *Monetary Backstops*; between equals it is all of it.
- **P5-6.** No chain or cycle can be built: pegging to an anchored country is refused in
  `can_ratify`, and a country whose anchor becomes anchored lapses next month.
- **P5-7.** Articles: the three appear in the treaty UI with their effects text; tooltips in
  `can_ratify` read correctly from both sides; an observer run shows AI signing pegs and swap
  lines, and **not universally**.
- **P5-8.** te_peg.2's three options: forced controls for 12 months (damp + fatigue, no JE
  needed); *Break* leaves the treaty and the index jumps to the shadow with imported
  inflation following; *Re-peg* drops the index by half the overvaluation and holds it there.
- **P5-9.** te_lolr.1 fires on the guarantor at a ward's default, once per five years; *Renege*
  zeroes every other ward's *Monetary Backstops* line for five years.
- **P5-10.** A pre-5a save holding `banking_fx_swap_lines` loads with no modifier and no
  error-log line; the FX Swap Lines row is gone from the dashboard and the AI's button list.
- **P5-11. §17 check 17** — a newly subjugated puppet shows kind 3 the next day and its rate
  tracks the overlord's within a month; released, it returns to its own rule within a month,
  with **no** exit penalty.
- **P5-12. §17 check 21** — does `.10`'s *Own flat minting* print a real figure for a subject
  with gold mines? If 0, `modifier:country_minting_add` is unreadable from script and the
  fallback is counting gold-mine levels. The overlord's gain is GDP-blind by construction
  and tiny for a colony without gold.
- **P5-13. §19 5c** — a board subject held at band 1 or 5 for six months gains
  *The Overlord's Rate* (+0.15 liberty desire); it clears the month the band leaves the
  extreme; alone it does not cause a revolt.
- **P5-14. §17 check 16** (bypassed, G10) — confirm `has_principle` /
  `has_principle_group` resolve for a mod-defined group: the *Monetary Union* row appears for
  every member of a bloc that takes the principle.
- **P5-15. §19 5b** — an adopter in a slump while the leader runs hot shows a tight band and a
  visibly rising *overvaluation premium*; adoption is refused outside the criteria and the
  debt line flips when the leader presses.
- **P5-16. §19 5b** — the exit invariant, with `.10` and `.9`: at 15 points of overvaluation,
  worse than staying for ≥ 5 years on treasury, SoL and radicals, better thereafter.
- **P5-17. §19 5b** — a pressed, debt-heavy adopter costs a tier-3 leader a backstop call
  within a cycle or two; pressing a bloc of refusers loses the leader cohesion on net (and an
  AI leader stops); a human holdout sees *The Question* fewer than ~6 times a campaign.
- **P5-18.** Phase 4's exit criteria still hold with phase 5 on — in particular "the 1836
  world sits at par": every board subject should read its overlord's par.

### 0.9 The `banking_system_simplified` game rule — 2026-09-21

**Owner request, implemented the same day.** `banking_system_rule` gained a third setting
between *enabled* and *disabled*. `banking_system_simplified` keeps the Banking Cycle journal
entry and **switches the whole of phases 1–5 off**: the mod's banking system then plays roughly
as it did before phase 1 — no rate to set, no inflation, no exchange rate, no international
arrangements. The cycle, its crashes, the prudential / command / cooperative tools, the
financial-regulation laws and the history charts are all unchanged.

**Owner decision on what the rate does under it (the one real choice here).** The rate stack's
*passive* half stays: `rate paid = world reference rate + risk premium`, so a country's cost of
borrowing still reflects its techs, rank, institutions, laws and debt — roughly §7.4's anchor
table — it simply cannot be steered. The alternative considered and **rejected** was
re-supplying vanilla's own interest sources in script (the flat 20%, the six rank multipliers,
laissez-faire, the five finance techs) to reproduce pre-phase-1 borrowing exactly; that would
have meant a second place mirroring vanilla numbers, to be re-checked on every vanilla bump
alongside the cancel-`INJECT`s.

**Why the passive half cannot be switched off with the rest.** §16.1's cancel-`INJECT`s are
file-level merges. No game rule reaches them, so with nothing in their place every country in a
simplified or disabled game would borrow at 0%.

**One trigger: `te_mon_full_system`** (`common/scripted_triggers/te_monetary_triggers.txt`) —
`has_game_rule = banking_system_enabled`, scope-free, so it reads from a country, a journal
entry, a treaty article, a power-bloc principle or the GUI alike. Its counterpart
`te_banking_system_on` (`banking_policy_triggers.txt`) is true for *enabled* **and**
*simplified* and is what the journal entry and the history store ask. **Nothing reads the game
rule directly any more.**

| Site | With `te_mon_full_system = no` |
|---|---|
| `te_mon_has_dial` | false everywhere — one line, and every consumer falls to its no-dial side |
| the monthly update | steps 0, 0b, 1, 4, 5, 7, 9 run; 1b, 1c, 5b, 6, 6c, 6d, 8, 8b, 9b, 10 are skipped |
| skipped steps' variables | keep step 0's seeds — `te_inflation` 0, `te_fx_index` par, `te_mon_anchor_kind` 0, `te_mon_stance_gap` 0 — so every downstream read is sane rather than missing. **This is the contract**: a step that is skipped never writes, and nothing needs a second "is it on?" test |
| step 4 | the **bankless spread is conditional** on actually being bankless; with the dial off for everyone, a country with a national bank would otherwise pay 1pp for not having one |
| `te_monetary_refresh_world_rate` | short-circuits to the era base, saving two ~200-country scans a month for an answer that cannot differ |
| step 5 | reduces to structural + debt load on its own: `te_mon_premium_fx` is 0 at par, `te_mon_premium_monetisation` 0 at level 0, `te_mon_premium_union_overvaluation` 0 for a non-adopter, and `te_mon_premium_unanchored` 0 because the expectation gap (0 against an anchor of 2 or 0) sits inside the 3pp tolerance |
| step 7 | the lenders' floor becomes `era_base`, and the realised-inflation subtraction is 0 |
| §16.3 stance channel | `te_mon_stance_gap` is 0, so momentum and bubble get nothing. `banking_cycle_apply_stance_band` is **not** gated: band 3 is already the designed answer for a country with no dial, and the stance bar already sits at its centre for one |
| OMO | reverts to its pre-phase-1 gate (unlock bool, 4 points, law lock); the `on_law_enacted` auto-switch-off is gated to match |
| capital controls | `ai_chance` falls back to the pre-phase-1 cycle rule on both sides — the external-crisis rule reads neutral inputs and would never fire |
| the ten FX-shock event options | call `te_mon_effect_fx_shock_tt`, which drops **both the shock and its tooltip line**, so no option promises a currency move that cannot happen |
| articles 110–112, `principle_monetary_union_1..3` | `visible = no` |
| dashboard / history | the Monetary Policy readout block is hidden (the two intervention rows under the same header are not); the inflation and FX charts are hidden and not sampled |

**`banking_system_disabled` now takes the same path**, which it always should have: with the
journal entry gone there was no UI for the dial, the bands or the hyperinflation chain, but the
whole simulation still ran behind it. This is a **behaviour change for that setting**, not just
for the new one.

**Known roughness: five modifier types still render on tooltips with nothing consuming them.**
`country_wage_pressure_add` (the ten labour / welfare laws of §9.4 plus UBI),
`country_policy_rate_drift_speed_mult`, `country_policy_rate_floor_add` and
`country_bank_forecast_error_add` (the national-bank / CBI laws), and
`country_inflation_pressure_add` (static modifiers). All five are granted from `modifier = { }`
blocks, which take no trigger, so a game rule cannot reach them — the same reason §16.1's
cancel-`INJECT`s cannot be switched off. Under the simplified setting a law tooltip therefore
still advertises, say, "Wage Pressure +0.4" in a game that has no wage pressure. Nothing is
wrong with the numbers; the line is simply inert. Fixing it would mean moving each term out of
the law and onto a script-managed modifier applied from the monthly update, which is a bigger
change than the rule is worth unless the tooltips bother the owner in play.

**Not verified in a running game**, like everything else in §0.

---

### 0.10 Phase 6 as shipped — rulings, deviations and open checks

Phase 6 (§19 rows 6a, 6b, 6c) was implemented on 2026-09-21, on top of §0.8/§0.9, in **one
change rather than the four PRs §15C.5's "Sequencing" line proposed** — the owner asked for
phase 6 as a whole. The sub-phases are still separable in the diff (6a is the hardening, 6b is
three modifier lines, 6c is two new article files plus the sites that had to learn the new
types), and 6c remains the first thing to cut. **Nothing below has been seen in a running
game**, and §0.8's P5-1…18 are still unrun, so 6a changes numbers that nobody has watched
settle yet: §15C.5 wanted P5-5, P5-7 and P5-9 seen once first, and they have not been. Every
offline check is clean — the parser on all fourteen touched files, the unit suite, `ruff`, the
tab check, the loc checks, `check_post_load_rosters.py`, and the nine audits in their CI
exit-code mode. **No `POST /reload` was run**: this was built in a container with no Victoria 3
install, so the eight audits that only run there (`loc_coverage`, `concept_reference`,
`localization_accessor`, `mod_structure`, `event_magnitude`, `modifier_visibility`,
`pm_employment`, `effect_trigger_validity`) have **not** seen these files. Run one before play.

**All thirteen owner rulings (§15C.5) are implemented as ruled**, including the three that
departed from the plan's recommendation: H5 (the prestige lines stay as shipped, and the plan's
managed `te_mon_arrangement_prestige` term was **not** written), H6 (nothing yearly of our own —
the two new score terms are the whole implementation, and the fallback walk is deliberately
absent until §17 check 22 says it is needed) and C4 (both pretexts are `in_default` only).

#### Deviations from §15C (phase 6)

| # | Deviation | Why |
|---|---|---|
| **P1** | **`te_mon_in_external_crisis` is now defined in terms of `te_mon_in_financial_crisis`**, rather than the two being parallel copies: the wide one is `OR = { is_at_war = yes te_mon_in_financial_crisis = yes }` | ruling H2 asked for "the same trigger without its `is_at_war` leg". Two hand-copied lists would drift the first time a fourth leg is added; one definition and a war leg on top cannot |
| **P2** | **The call counter is incremented FIRST, and a derived `te_mon_lolr_calls_prior` prices the call in flight** | §15C.1 says "incremented by `te_monetary_on_country_default` when it fires `te_lolr.1`", but its four schedules disagree about which side of the increment they want: the relief taper wants the post-increment count (`n = 1` after the first default), while the honour cost, the AI odds and the cooldown want the prior count (the first call costs 5%, not 7.5%). The file's rule is now one line long — **what prices THIS call reads `_prior`; what prices the ONGOING relationship reads the counter** — and it is stated at the increment, in the values file and in the event header |
| **P3** | **`te_lolr.1`'s odds saturate at `n = 3`**, at the tabled 10 − 3n : 2 + 2n = 1 : 8, instead of continuing | `ai_chance` bases are weights; a fourth call driving Honour to −2 is not "worse than 1:8", it is undefined. Three `>=`-tiered modifiers give exactly the tabled walk and then stop |
| **P4** | **The Backstops row's *drawn / limit* line is a customizable-localization clause appended to the row's value**, not a new row | one row, one fact, and the clause is empty for everybody not drawn — which is almost everybody, since a line is only drawn in a financial crisis. No `.gui` change was needed |
| **P5** | **The harness is a new `te_debug_monetary.11`, not more options on `.10`** | §15C.1 offered the choice; `.10` already carries six options and a read-out that fills the window. `.11` pins a debug swap line the way `.10` pins a debug anchor (`te_mon_debug_swap_on`, honoured by the discovery), forces one month of financial crisis, and cycles the call counter |
| **P6** | **A new `te_mon_has_swap_line_role` trigger** wraps "holds the recipient role, by treaty or by debug pin" | the settle-on-role-end check and the role branch must agree about what "the role ended" means, or the debug line settles itself every month |
| **P7** | **6c's pretexts are tested twice — symmetrically in `possible`, directionally in `can_ratify`** | `treaty_articles_reference.md`'s own rule: "Symmetric conditions in `possible`; everything directional in `requirement_to_maintain` or `can_ratify`". `possible` runs before the direction is fixed, so `scope:source_country` / `scope:target_country` are not the right handles there. `possible` asks whether a pretext exists in *either* direction; `can_ratify` holds the imposer to the side that has one, and carries the tooltip |
| **P8** | **`te_mon_is_imposed_pegger` is a live treaty walk, not a stored flag** | the anchored state has one pair and one kind; *which article* put a country there is a property of the treaty. Three consumers read it (the spread, the standing cut, `te_peg.2`'s missing Break), each at most once a month for an anchored country, so it costs one extra walk per anchored country per pulse — the same cost class as the discovery itself |
| **P9** | **113 carries no `non_fulfillment` on war or expelled diplomats**, unlike the friendly three (H7) | a chosen peg between belligerents should end, because it is a mutual arrangement. An imposed one is the settlement a war produced, and a renewed war is exactly when the imposer wants it standing. The enforce play is the way out, for either side |
| **P10** | **114's `can_ratify` drops the separate `te_backstop_provider_outranks_tt` line, and its `requirement_to_maintain` gets its own `te_receivership_receiver_solvent_tt` rather than reusing 112's** | `te_mon_can_receive_for` already contains `te_mon_can_backstop` with the roles swapped, and its own tooltip names both halves — two tooltips for one test is noise. §15C.3 named 112's solvency key as the *check* to reuse; the key's text says "the guarantor", which is the wrong noun for a commission, so the trigger is shared and the wording is not |
| **P11** | **The two pretext tooltips name no country** | no mod treaty-article tooltip resolves `SCOPE.sCountry('source_country')`, and there is no precedent for that scope being exposed to loc from `can_ratify`. The wording carries the rule without the handle |
| **P12** | **A receivership's relief is `te_mon_lolr_relief`, so it tapers by the debtor's own `te_mon_lolr_calls`** | the value was reused deliberately rather than duplicated. A debtor that has already burned two guarantors is worth less to a receiver too — and its default *under* the receivership pays it nothing and moves no counter, because `te_monetary_on_country_default` tests the guarantee and a receiver is a creditor, not a guarantor |
| **P13** | **A new `te_mon_has_treaty_debt_relief`** (guarantee-or-receivership) replaces the bare `te_mon_lolr_is_effective = no` guard on 5b's tier-3 backstop | §15A.3's rule is "two guarantors of one debt are not two rescues". A receiver is the third way to be relieved and had to join the same test |

#### Known roughnesses (phase 6)

- **`te_mon_anchor_spread` now performs a treaty walk** (P8) at the one site that sets an
  anchored country's rate. If a profile ever shows it, the fix is a stored `te_mon_anchor_imposed`
  flag written beside `te_mon_anchor_kind` in `te_monetary_anchor_changed`.
- **The engine-built `*_effects_desc` keys for 113 and 114 are hand-written**, in
  `te_unused_l_english.yml`, like every other article's — §0.8's known roughness, unchanged.
  The three shipped articles' keys were also rewritten for 6a's and 6b's changes, so they are a
  second place that has to move when the constants do.
- **Nothing was done about §15B.3's "general pattern"** beyond what H6 ruled: the weak side's
  flat `+10 / +20 / +20` eagerness still carries no caution term. That is the ruling, not an
  omission — but it is the thing to revisit first if observer runs show AI minors signing
  everything offered.
- **The AI's post-signing withdrawal is unimplemented by design** (H6). Until §17 check 22 is
  read, an AI guarantor whose ward has defaulted three times is relying on the engine to act on
  a score that has gone deeply negative. If the check fails, §15C.1 carries the fallback walk
  ready to write.

**Not verified in a running game**, like everything else in §0.

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
per-state monetary effects. No full FX system in phases 1–3 (designed for phase 4 in §15).

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
| Credit standing + risk premium | exact, each with a per-source breakdown tooltip | `te_premium_structural`, `te_premium_cyclical` (§7) |
| Inflation / expected inflation (P2) | exact, 1 decimal | `te_inflation`, `te_inflation_expected` |
| **Policy stance** | **band only**: very loose / loose / neutral / tight / very tight | the bank's *estimate* of (real rate − neutral rate) |
| World rate (P3) | exact (a **real** rate) | `global_var:te_world_rate` |
| Gold flow per month, peg confidence (P3) | exact flow; confidence as a bar | — |
| Exchange rate (P4) | exact index, 100 = par, with a per-term breakdown; "Par (convertible)" on metal | `te_fx_index` (§15.1) |
| Overvaluation (P4, pegs) · monetary anchor (P5) | overvaluation exact; anchor named | `te_mon_overvaluation` (§15.2), `te_mon_anchor` (§15A.1) |
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
policy_rate   drifts toward target at 1/3 pp per month     has a dial: national bank on commodity money
                                                            (narrowly, §0.6) / gold / fiat / digital
              = world_rate + expected_inflation + 1.0       no dial: no national bank, or crypto with or
                                                            without one
              = administered_rate                           command economy
              = anchor's policy_rate + spread               anchored — phase 5, §15A.1

market_yield  = max( policy_rate , era_base + expected_inflation )      phase 2 (§10); = policy_rate before

rate_paid_pts = clamp( market_yield
                       + max( floor , structural_premium )              §7
                       + cyclical_premium
                       − inflation                                      phase 2
                     , 0.5 , 60 )
```

The policy rate is **nominal**; the world rate (§12.1) is **real**. A no-dial country's
`te_policy_rate` is derived, never discretionary, and is excluded from the world-rate
average.

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

- **Dial:** integer target, 1pp steps, range by regime (§5) — five settings wide under
  commodity money, 0–15 on gold, 26 or 29 under fiat / digital. Drift 1/3 pp per month
  (1pp per quarter). A 5pp swing takes 15 months — reversals are slow by construction.
  A **delegated** target is the mandate formula rounded to the nearest integer, with
  hysteresis (it only moves when the formula differs from the current target by ≥ 0.75) so
  it never flaps.
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
| `law_commodity_money` | **`world_rate − 1` to `+ 3`** with a national bank (five settings); **none** without one | the world price of the metal — the band is the constraint, and there are no specie flows behind it (§0.6 R5) | no monetisation, no QE; expected inflation pinned to 0; the bankless spread only while bankless |
| `law_gold_standard` | target 0–15 | **gold flows** (§12). Interim before P3: target clamped to `era_base` ±2pp | credibility: premium −1pp; expected inflation anchored at 0; deflation bias; **no QE** — its crisis tool is suspending convertibility (§12.3, phase 3) |
| `law_fiat_currency` | target 0–25 | **inflation** (§9) | monetisation lever; QE at the floor; no credibility bonus — it must be earned |
| `law_digital_currency` | target **−3**–25 | inflation | negative rates (no cash to hoard); drift twice as fast (better transmission) |
| `law_decentralized_cryptocurrency` | **none** | pays world rate + spread | fixed supply: inflation pulled toward −1%; no monetisation, no QE, no lender of last resort |

The existing volatility modifiers on these laws stay. **Minting is the missing fiscal axis
(proposed — owner to decide).** Vanilla minting *is* seigniorage — roughly 5% of GDP a year
(§11) — and the ladder currently ignores it on the two rungs where it matters most:

- `law_decentralized_cryptocurrency`: the state keeps 100% of minting on a currency it by
  definition does not issue. A large negative `country_minting_mult` (−0.75) is *the* price
  of crypto; today its only fiscal cost is −15% tax capacity.
- Fiat +10% / digital +25% minting: under this design they are no-tradeoff bonuses on the
  rungs whose identity is "autonomy at the price of discipline". Keep them as modest
  baseline efficiency, or fold them into monetisation-lever strength — but decide it.

This gives each law a real identity: commodity money buys a discount rate you can lean
with but not steer by; gold buys credibility and cheap borrowing at the price of autonomy;
fiat buys autonomy and war finance at the price of discipline; crypto is commodity money
without even the discount rate.

**When each rung opens.** Commodity money is ungated; `law_gold_standard` at
`central_banking` (era 2 — moved there 2026-09-21, §5.4); `law_fiat_currency` at
`keynesian_economics` (era 6) **and** `law_national_bank`; `law_digital_currency` at
`universal_digital_identity` plus the bank; `law_decentralized_cryptocurrency` at
`cybersecurity`. The gate is availability, not adoption: what paces the ladder is §13's
politics and the AI enact weights, not research.

### 5.2 `lawgroup_national_bank` and `lawgroup_financial_regulation` — who holds the dial

| State | Control |
|---|---|
| `law_no_national_bank` | No policy rate. Country pays world rate + own expected inflation + 1pp spread + premium (§4). |
| `law_national_bank` | Player sets the target, **or** delegates it to a mandate (§6). |
| `law_national_bank` + `law_central_bank_independence` | Mandate is **binding**. No manual target, no monetisation. In return: premium floor 0.25 (vs 0.5), premium −0.5pp, expected inflation anchors twice as fast, smaller estimation error. |

| `law_national_bank` + `law_state_owned_banking` outside a command economy **(proposed)** | The opposite pole from CBI: full political control. Dial and delegation as normal, but the lowest credibility (anchor c = 0.15, no CBI bonuses, structural premium +0.5) — and the state bank absorbs the debt, so monetisation carries no premium surcharge. Under `law_command_economy` the administered rate (§5.3) applies instead. |

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
- **Resolved (2026-09-21, §0.6).** France 1836 has a national bank on commodity
  (bimetallic) money, and the Banque de France did set a discount rate. It now gets the
  narrow dial this line proposed, reshaped to `world_rate − 1 … + 3` (§0.6 R2) — rather than nothing
  until it enacts gold. Commodity money without a bank is unchanged.
- **The gold standard's tech gate: `central_banking` (era 2), moved 2026-09-21 from
  `international_exchange_standards` (era 4).** The law is a *unilateral* convertibility
  promise — Britain 1816, Portugal 1854, Germany 1871, the US 1873 — not membership of the
  1870–1914 settlement network the era-4 tech models, and the era-4 gate (mod eras:
  `common/technology/eras/00_eras.txt`, era 4 = 1887–1911) put the law fifty years behind
  the first bullet's own GBR start. It now sits with its siblings: `law_national_bank` and
  `law_universal_banking_light_prudence` are both at `central_banking`,
  `law_free_mutual_banking` at `postal_savings`. What paced adoption historically was
  politics, not technology, and §13 already models that — `cross_of_gold_currency` on the
  agrarian and isolationist baselines, plus the enact weight — so the gate is permissive and
  the politics do the pacing: with research and enactment lag the wave lands c. 1860–1875
  (Germany 1871–73, Scandinavia 1873–75, the Netherlands 1875, France 1876–78, the US 1879).
  **The peg articles do not follow it down.** `currency_peg` / `imposed_currency_peg` /
  `debt_receivership` stay at `international_exchange_standards`: §15A.2's staggering (peg,
  then swap line at `macroeconomics`, then guarantee at `intergovernmental_organizations`)
  is independent of where gold sits, coherence needs only peg gate ≥ gold gate, and a
  *negotiated* peg between currencies is the later, treaty-borne form of the thing — so
  110_currency_peg.txt's gate comment, which justified era 4 as "the tech that brings the
  Gold Standard law in with it", was rewritten rather than acted on. **Open:** §17's observer
  runs were calibrated on "Britain is the only tag on gold with a bank" in 1836. That still
  holds on day one — no start tech grants `central_banking` — but a 50-year run now sees
  several gold countries by mid-century, so re-read the §12.1 world rate and §7.4's anchor
  figures after the change rather than assuming the phase-1/2 exit numbers carry over.

---

## 6. Delegation, mandates, independence, AI

**Delegation** is a free toggle for any national-bank country. While delegated, the monthly
update sets the target from the mandate formula instead of the player's stepper.

| Mandate | Target formula (clamped to the regime's range) | Character |
|---|---|---|
| **Price stability** | `r̂* + π + 1.0 × (π − 2) + cycle_lean` | leans against inflation first; accepts slumps. (Sanity check: at π = 13 this asks for ~26%, clamped to 25 — Volcker territory; a plain Taylor weight of 0.5 would give ~20%) |
| **Growth** | `r̂* + π − 1.0 + 0.5 × max(0, π − 4) + cycle_lean/2` | runs 1pp warm — equilibrium inflation ≈ 2 + 0.4/c ≈ 3% — and reacts only above 4% (zero-gap point π = 6), or frenzy. Never more hawkish than price stability |
| **Peg defence** (gold only) | `world_rate + 0.5 × reserve_shortfall_pp` | keeps gold flows at zero; ignores the domestic cycle |

`π` in these formulas is **core** inflation (§9.1) — mandates look through cost-push.
`r̂*` is the bank's **estimate** of the neutral rate: true value plus a slow random-walk
error of ±1.5pp (±0.5pp under CBI; shrinking with finance techs). `cycle_lean` is the
replacement for the deleted rate-hike button's AI logic: +2 frenzy, +1 boom, +1 if bubble
pressure ≥ 65, −2 recession, −3 panic.

**Phase 1 has no inflation, so every π term is dropped — including the −2 target.**
Price stability is `r̂* + cycle_lean`; growth is `r̂* − 1.0 + cycle_lean/2`. (Plugging
π = 0 into the full formulas instead would give `r̂* − 2` and leave every delegated fiat
country 2pp loose for the whole phase.) Growth's standing 1pp looseness is its point: more
momentum, faster bubble build-up, more crash risk.

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

A national-bank country **without the JE** (no `stock_exchange` or no level-5 urban
center) has no dashboard and is auto-delegated to price stability.

---

## 7. Risk premium

`rate paid = policy rate + risk premium`. The premium is computed from visible modifier
contributions in **two tiers**, because a single floored sum does not work: a mature great
power's standing sits ~3pp *below* the floor, so a single floor would silently swallow a
panic (+2), every tool, most event outcomes and the whole debt-load term — their tooltips
would say "+2.0%" while the rate paid did not move.

| Tier | What it is | Sources | Floor |
|---|---|---|---|
| **Structural** — *credit standing* | what the country *is* | access, rank, techs, institution level, laissez-faire, gold / CBI credibility, company prosperity | **floored** at 0.5 (0.25 under CBI) |
| **Cyclical** — *risk premium* | what is *happening* | cycle phases, tools, crash interventions, event outcomes, Great Depression, bankruptcy, debt load, monetisation, unanchored expectations, colonial/treasury-strain modifiers | added **after** the floor |

Standing beyond the floor is wasted by design — credibility has a lower bound — but a
crisis always bites. Cyclical *negatives* (relief tools) can pull the total under the
structural floor; the §4 clamp (0.5) is the final backstop.

### 7.1 Modifier types

Two new script-only types in
`common/modifier_type_definitions/banking_cycle_modifier_types.txt`:

```
country_credit_standing_add = { color = bad percent = yes decimals = 1 script_only = yes game_data = { ai_value = 0 } }   # structural
country_risk_premium_add    = { color = bad percent = yes decimals = 1 script_only = yes game_data = { ai_value = 0 } }   # cyclical
```

Vanilla's scale (0.01 = 1pp) so there is one unit convention across the mod. Tooltips read
"Credit standing: +1.0%" / "Risk premium: +2.0%". Each needs name + `_desc` loc in
`localization/english/te_modifiers_l_english.yml` (the engine gives no warning for missing
loc), and literals ≥ 0.0005 to pass `modifier_visibility_audit`.

```
te_premium_structural = max( floor , 100 × modifier:country_credit_standing_add )     floor 0.5 (0.25 CBI)
te_premium_cyclical   = 100 × modifier:country_risk_premium_add + computed terms (§7.6)
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
level-5 urban center) is not a capital-market signal.

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
| Decentralized | — | +10.0 (no rank term would let it borrow cheaper than a minor power) |

### 7.4 Anchor table (phase-1 exit test; world/reference rate = `era_base` = 3, inflation 0)

| Case | Build-up | Pays | Vanilla today |
|---|---|---|---|
| Britain 1836 (gold, bank; `banking` + `central_banking`; interventionism) | 3 + structural (0.5 rank + 1.5 access − 1 gold − 0.6 bank = 0.4 → **floor 0.5**) | **3.5%** | ~8% |
| USA 1836 (no bank; major power; same two techs — tier-1 starting tech grants `central_banking`) | 3 + 1 spread + structural (1 rank + 1.5 access) | **6.5%** | ~12% |
| Siam 1850 (tier-4 tech: no finance techs, no exchange) | 3 + 1 spread + structural (6 rank + 8 access + 2 no exchange) | **20%** | ~35% |
| Late-game GP, target 3% | 3 + structural (0.5 rank − 0.5 laissez-faire − 1.5 bank − 1.8 mod techs = −3.3 → **floor 0.5**) | **3.5%** | **~0.2%** |
| Same GP in a panic, after default | 3 + structural 0.5 + cyclical (2 phase + 10 bankruptcy) | **15.5%** | ~0.4% |

Consols yielded ~3.3% in 1836, so the Britain row is on target.

### 7.5 Converting every existing source

**Rule for the mod's flat `_mult` modifiers: pp = mult × 20**, snapped to 0.1pp — the value
the mult had against vanilla's unranked 20% base. Everything in the table below is
**cyclical** (`country_risk_premium_add`) except `institution_national_bank`, which is
**structural** (`country_credit_standing_add`) along with the access, rank, tech,
laissez-faire and credibility terms of §7.2–7.3.

| Group | Today (`_mult`) | Becomes (pp) |
|---|---|---|
| Phases: panic / downturn / stagnation | +0.10 / +0.05 / +0.02 | +2.0 / +1.0 / +0.4 |
| Tools: deposit guarantee / emergency liquidity / FX support / FX devaluation / coop credit expansion | −0.01 / −0.04 / −0.01 / +0.02 / −0.03 | −0.2 / −0.8 / −0.2 / +0.4 / −0.6 |
| Tools: **rate hike / OMO** | +0.05 / −0.04 | **interest field deleted** (the dial replaces it; OMO → QE, §11) |
| Crash interventions (6) | +0.02 … −0.06 | +0.4 … −1.2 |
| Banking event outcomes (13) | −0.10 … +0.20 | −2.0 … +4.0 |
| Great Depression / bystander | +0.15 / +0.05 | +3.0 / +1.0 |
| Crisis capital controls / monetary stabilisation | +0.05 / +0.08 | +1.0 / +1.6 |
| `colonial_military_garrison_modifier` | +0.05 | +1.0 |
| **Hand-judged:** `declared_bankruptcy` | +0.50 | **+10.0** |
| **Hand-judged:** `institution_national_bank` | −0.05 / level | ~~−0.3 / level~~ **−0.15 / level** — *revised 2026-09-20:* −0.3 was judged against vanilla's cap of 5 levels; this mod's `MAX_INSTITUTION_INVESTMENT` is **9**, so −0.3 made a fully-funded bank worth −2.7pp, more than gold, CBI, laissez-faire and all five mod techs together. −0.15 × 9 = −1.35, the ceiling that was meant. §7.4's Britain row loses 0.3 of its "−0.6 bank" and still reaches the 0.5 floor once invested |

The mod's existing `_add` users re-type too. Cyclical:
`treasury_strain_persistence_modifier` (+0.5), `neocolonial_dependency_imposed_modifier`
(+1.0), `finreg_interest_rate_hike` (+1.0 — a law-stall event modifier, unrelated to the
deleted button despite the name). Structural: the two Shell sources (−1.0 → −0.3), and the
mod's five techs (`era_6.txt:172`, `era_8.txt:93`, `era_9.txt:561`, `era_10.txt:300` at
−2pp; `era_12.txt:376` at −1pp), which drop to **−0.4pp each (−0.2 for the era-12 one)** —
at realistic levels −2pp is a third of the whole rate.

**Vanilla, cancelled at source** with inverse `INJECT`s that carry the new premium in the
same block (precedent: `common/laws/sol_expectations_vanilla_injections.txt:9-23`, shipped
since April): six country ranks, `law_laissez_faire` (−0.25 → −0.5pp), five finance techs.
This is the owner's "convert the big multipliers" decision.

**Vanilla, deliberately left alone** (owner: widen only if balance demands): IG traits
(−0.075…−0.15), amendment mults (−0.1/−0.2), companies, character trait, event modifiers.
Consequence to document in the tooltip: these still *multiply* the whole stack, so a −20%
amendment is −20% of (policy + premium).

**Vanilla `_add` amendments — accepted explicitly, first in line to convert.** Five
enactment amendments (`00_amendments_enactment_04.txt:644,1138,1174,1222,1266`) carry
`country_loan_interest_rate_add` +0.02 / +0.02 / +0.03 / +0.01 / +0.05. They bypass both
premium tiers and the dashboard breakdown, and rebasing makes them ~4× heavier: +5pp on a
~3.5% rate more than doubles it — the same argument that cuts the mod's techs above. They
are left alone in phase 1 because they are rare, always positive (they can never push the
rate to ≤ 0) and read naturally as lender disapproval — `amendment_foreign_investment_seizures`
at +5pp is about right. If play shows them dominating, convert with five cancel-`INJECT`s
at ×0.4. This is the first "widen the surgery" candidate.

**Generator trap.** `scripts/generators/gen_banking_events.py:2085-2155` embeds six
`country_loan_interest_rate_mult` modifiers and appends them to `extra_modifiers.txt`. It is
a one-shot script (not in `docs/auto_generated_files.md`). Update its strings or mark it
do-not-rerun.

### 7.6 Computed premium terms **(proposed)**

All three are **cyclical** — added after the structural floor, so they always bite.

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

The gap (clamped to ±4 for this purpose, so steady-state momentum stays inside the ±5 bar)
acts on the cycle **through the variable update, not through a visible modifier**:

| Effect | Per pp of **tight** gap | Calibration | Delivery |
|---|---|---|---|
| `finance_cycle_momentum` | −0.125 / month | a 2pp tight stance = the old rate hike (−0.25) | `change_variable` inside `banking_cycle_advance_variables` |
| `bubble_pressure` | −0.75 / month | 2pp ≈ −1.5 (old hike: −2.0; old OMO: +0.8) | same |
| `state_capitalists_investment_pool_contribution_add` | ∓0.02 / ∓0.04 by band | cheap money feeds the pool | five **banded** JE-scope static modifiers keyed to the *displayed* stance band |

Loose gaps apply the opposite sign.

**Why not a scaled modifier.** A `banking_monetary_stance` modifier scaled by the true gap
would print `−0.125 × (policy − π − r*)` in its tooltip, and r\* = policy − π + momentum/0.125
could be read to two decimals from the JE's modifier list — undoing §3 and §20 risk 6 in
the phase that ships first. **The rule:** what the player *chooses* is shown exactly (laws,
tools, the target, wage pressure in §9.4); the economy's *hidden state* (r\*, and the
momentum and bubble numbers the dashboard already bands) is never printed. The stance's
effect size depends on r\*, so it is hidden state. The momentum tooltip gains a line
"Policy stance: [band]" instead of a number, and the banded pool modifier leaks nothing the
band does not already show. The cycle's ±1 monthly random nudges dwarf 0.125/pp, so the
history charts do not give r\* away either. Side benefits: no JE-scope multiplier wrapper,
and no one-month lag.

**Who feels the stance: only countries with a dial** (§4). For a no-dial country the
"policy rate" is world + spread ≈ 4 against a neutral near 3 — applying the channel would
leave every `law_no_national_bank` country permanently tight, a hidden penalty nobody
chose. A market rate clears at neutral by definition, so bankless, crypto and
command-economy countries get **stance gap = 0** (commodity money *with a bank* left this
list in §0.6 — it sets a rate, so it has a stance). The same logic sets the interim
reference rate to `era_base` rather than a constant (§12.1): a gold country on peg defence
targeting a fixed 4 against a neutral of 3 would be permanently 1pp tight. What they give up is the
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

`te_inflation` (headline) is a signed annual %, clamped −10…100. It is a slow-moving
**core** plus a transient cost-push term. `te_inflation_expected` is what lenders and the
mandate formulas look at. Headline and expected are exact on the dashboard.

### 9.1 Monthly update

Every driver is a **level** in pp — "how far above expectations inflation settles while
this lasts" — never a per-month increment. (An earlier draft added drivers to Δπ directly;
that made a routine 10% grain move worth ~28pp of cumulative inflation, and made a labour
law accelerate inflation forever.)

```
pressure (pp) =
    − 0.4 × stance_gap (clamped ±4)          loose money
    + phase term                             frenzy +1.5 · boom +0.8 · expansion +0.3 · stable 0
                                             stagnation −0.3 · downturn −0.8 · panic −1.5
    + 0.2 if bubble_pressure ≥ 65
    + 0.3 × max(0, deficit % of GDP − 1)     ×2 at war
    + 2.5 × monetisation_level               §11
    + 1.0 if QE active                       §11
    + 100 × modifier:country_inflation_pressure_add          wage pressure, §9.4; also event modifiers (§11)
    + 0.5 × gold flow in % of GDP per year   phase 3, §12.2 — inflows inflate, outflows deflate
    − 2 × max(0, π_core − π_world − 1)       commodity money only, clamped at −6 — §0.6 R7, the
                                             price-specie channel a regime with no vault gets instead
    + gold-supply term                       metallic regimes only, see below
    + regime pull                            gold / commodity: −π_core · crypto: −(π_core + 1)

π_core     += 0.10 × ( expected + pressure − π_core )        ~10-month adjustment
π_headline  = π_core + cost_push                             §9.3 — a level term, clamped ±6

anchor      = 2 (the mandate target); 0 on gold / commodity (pinned, c = 1)
c_eff       = c × max( 0 , 1 − |π_headline − anchor| / 10 )       credibility is lost as inflation leaves target
expected   += α × ( (1 − c_eff) × π_headline + c_eff × anchor − expected )
```

| | α (speed) | c (credibility anchor) |
|---|---|---|
| Manual target | 1/24 | 0.25 |
| Delegated, not CBI | 1/24 | 0.4 |
| Central bank independence | 1/12 | 0.7 |
| Gold / commodity money | — | 1 (expected pinned to 0) |

The **real rate, the rate paid and the bands use headline**; persistence acts on core; the
**mandates react to core** — a delegated bank *looks through* a supply shock and responds
only to its second-round effects (simulated, +25% grain under price stability: policy peaks
at 7% reacting to core against 9% reacting to headline, for a 4.5% headline peak either
way). A manual player gets no such help: that is the stagflation dilemma.

The credibility anchor **(proposed)** is what "CBI anchors expectations" means
mechanically: with a standing pressure P *and the real stance held* (the rate moving with
inflation, as any mandate does), inflation settles at 2 + P / c instead of accelerating —
+0.5pp of wage pressure costs 2pp of inflation at c = 0.25 but 0.7pp under CBI.

> **As shipped, "2 + P / c" is the small-P linearisation, not the whole story** (§0.4, owner
> decision A). With the de-anchoring `c_eff` below, the equilibrium gap `g = π − anchor` has
> to satisfy `c × (1 − g/10) × g = P`, whose left-hand side peaks at `g = 5` with the value
> **2.5 × c**. So there is **no fixed point at all** once `P > 2.5 × c` — 0.625pp on a manual
> target, 1.0pp delegated, 1.75pp under CBI; a boom phase alone clears the manual threshold.
> That is consistent with the instability paragraph below and sharper than it, because it
> bites on a *held real* stance rather than only on a pegged nominal one. The code is
> spec-faithful; the harness's third sequence is where to watch it.

**A fixed manual target is unstable above the floor, by design.** Holding the nominal rate
fixed while π rises lowers the real rate, which adds pressure: stable only if c > 0.4, so
on a manual target (c = 0.25) inflation drifts away with an e-folding time of several
years. That is the Taylor principle — a nominal-rate peg is not a policy — and it is slow
enough that answering it is a few target changes per cycle, not micromanagement.
Delegation is the set-and-forget option. Because AI countries are always delegated, an
observer run never exercises this path: phase 2 needs a **debug harness** that pins a fiat
tag to a fixed manual target (§19).

**Credibility de-anchors.** `c_eff` falls to zero once inflation is 10pp from target (gold
and commodity money are exempt — convertibility *is* the anchor). Without this, an anchored
`expected` would trail a *steady* high inflation forever and the §10 lenders' floor would
under-price it permanently.

**The regime pull is a proportion, not an anchor** (issue #351). With expectations pinned at
0, a pull of `−π_core` makes the fixed point `π_core = X − π_core`: hard money settles at
*half* of everything else in the sum, closes a constant fraction of the gap forever and
never reaches zero, and doubling the other pressures doubles the equilibrium inflation. That
is the deflation *bias* §5.1 describes, and it is not a price *level* anchor. Each
convertible regime needs a quantity channel of its own beside it — gold flows for a gold
standard, and since 2026-09-21 the commodity-money price-specie term above (§0.6 R7). Its
input is phase 4's `te_mon_fx_term_inflation`, normalised out of the FX weight, so the
"which inflation is this currency judged on" rule of §15.2 — realised core on metal — is
stated once. **The tolerance is the floor of the regime:** the equilibrium solves
`π_core × (2 + per_pp) = X + per_pp × (π_world + tolerance)`, so no slope holds a commodity
country below `π_world + tolerance`, and the clamp is what still lets a debasement or a
monetised war inflate.

**Gold supply (proposed).** §5.1's "deflation bias" under metallic money should not be a
constant: historically it *was* gold supply lagging output, and the reversals were
discoveries — California and Victoria in the 1850s, the Rand and the Klondike ending the
Long Depression. The engine already models supply as `country_minting_add` on gold-mine
PMs (vanilla 125–1000 per level; the mod's late PMs reach 8250). Term:
`k × (gold-mine minting ÷ GDP − its own slow trend)` for the country's market, so a gold
rush is a monetary event. Natural phase-3 companion: mine output as a positive input to
`te_peg_confidence`.

**Deficit % of GDP — units trap.** The term reuses the shape of
`financial_cycle_government_fiscal_policy_effect_size`
(`common/script_values/extra_script_values.txt:1808`), computed in country scope — but
budget flows (`income`, `total_expenses`) appear to be **weekly** while `gdp` is **annual**
(the mod's own `sv_money_flow_event_small = gdp × 0.0001` is commented "0.01% GDP / week"),
which would make that expression 52× too small; its own comment, "was effectively dormant
at typical 1–3% deficit levels", fits. VERIFY IN-GAME (§17 check 12); if confirmed this
term needs ×52, and the existing fiscal-policy input has the same bug. Also **exclude
minting from `income`** here, or monetisation suppresses its own deficit term.

### 9.2 Bands and consequences

| Band | π | Consequences (one scaled static modifier per band; validate every name via `/modifier-search`) |
|---|---|---|
| Deflation | < −1 | momentum drag; Rural Folk + Trade Union anger (debtors); rate paid **rises** via §10 |
| Comfort | −1…3 | none; **real-wage dividend** active (§9.4) |
| Elevated | 3…8 | lower-strata cost-of-living squeeze (candidate: `country_sol_expectations_lower_offset_add`); Petite Bourgeoisie − |
| High | 8…20 | + `state_tax_waste_add` (collection lag); Landowners / Armed Forces − (fixed incomes); investment-pool efficiency − |
| Very high | 20…50 | all of the above, steeper; bubble pressure + (flight to real assets); **`country_minting_mult` −0.3** — real seigniorage follows a Laffer curve and collapses in a flight from the currency |
| **Hyperinflation** | ≥ 50 | **`country_minting_mult` −0.8**; crisis state + event chain: currency reform (reset π and expected to 5; investment-pool wipe-out, radicals, +5pp premium for ten years) / dollarise (adopt a no-policy regime **and lose seigniorage**: `country_minting_mult` −0.75, the defining cost of dollarisation) / ride it out |

These bands are the **deterrent against never disinflating** (§10), so they must be sized
for that job, not as flavour.

### 9.3 Cost-push — the goods basket

Goods prices are real relative prices capped at 0–2× base, so a *level* is not inflation: a
world where oil is permanently dear is just a fact about that world. Only **changes** are
inflationary:

```
index      = Σ weight × (price / base − 1)      per market
cost_push  = 0.3 × (index − basket_avg) × 100 , clamped ±6pp     added to HEADLINE, not to Δπ
basket_avg += (1/36) × (index − basket_avg)
```

**Phase 4 adds a second input inside the same clamp** — imported inflation,
`0.15 × (te_fx_avg − te_fx_index)`, the identical change-not-level construction applied to
the currency (§15.3).

It is a **level** term: a 10% grain rise (index +0.03) lifts headline by ~0.9pp and fades
over three years as the average catches up; oil doubling lifts it ~4.5pp. It never
accumulates. It reaches core only through expectations — (1 − c) of headline feeds
`expected`, and core chases `expected` — so the shock persists exactly to the extent the
central bank lacks credibility or accommodates it.

| Good | Weight | | Good | Weight |
|---|---|---|---|---|
| grain | .30 | | fish | .075 |
| clothes | .15 | | meat | .075 |
| coal | .15 | | wood | .05 |
| oil | .15 | | fabric | .05 |

This is the 1970s, and the source of the stagflation dilemma: hike into a slump, or
tolerate it and let expectations drift.

Implementation: reuse the shipped numeric price-ratio idiom `st_res_<good>_price_rel`
(`common/script_values/st_res_script_values.txt:1054-1078`; rationale
`strategic_reserve_system.md:204-212`). **Block form only** — that doc warns the dot-chain
form may silently read zero. Exclude `local = yes` goods. **Seed `basket_avg` to the first
observation** or month 1 produces a phantom shock; **re-seed it when the country changes
market** (joining a customs union moves the index for reasons that are not inflation). Performance option: compute once per market owner, members read
`market.owner.var:`. VERIFY IN-GAME: reading `mg:oil` in a market that has never traded oil
— gate that term on the tech if it errors.

### 9.4 Wage pressure and the real-wage dividend **(proposed)**

New *visible* script-only type `country_inflation_pressure_add` (pp of standing pressure in
§9.1, same scale and registration as §7.1), placed on labour laws so the effect is never
hidden:

| Law | Wage pressure (pp) |
|---|---|
| `law_no_workers_rights`, `law_combination_acts`, `law_anti_strike_laws` | −0.2 |
| `law_regulatory_bodies`, `law_right_to_associate` | +0.2 |
| `law_worker_protections`, `law_corporatized_unions` | +0.4 |
| `law_factory_councils` | +0.5 |
| welfare: `law_wage_subsidies` +0.2 · `law_old_age_pension` +0.2 · `law_universal_basic_income` +0.5 | |

**Compensation**, so this is not a hidden tax on progressive laws: while inflation is in
the comfort band, each +0.1pp of wage pressure also yields a lower-strata loyalist trickle
and +0.03 `country_finance_momentum_monthly_add` (wage-led demand). Outside the band the
dividend switches off and above 8% the same laws add to persistence (wage-price spiral).

The arithmetic, for `law_factory_councils` (+0.5pp): inflation settles 0.5 / c higher.
On a **manual** target (c = 0.25) that is +2pp — out of the comfort band unless the player
holds a stance 1.25pp tighter (−0.16 momentum/month), which the dividend (+0.15) roughly
cancels: a wash on growth, a gain in loyalists. Under **CBI** (c = 0.7) it is +0.7pp —
still inside the band with no tightening at all, so the dividend is pure gain. Strong
labour laws are *better* under credible monetary management, not uniformly worse.

---

## 10. Debt: expected versus actual inflation

```
market_yield  = max( policy_rate , era_base + expected_inflation )
rate_paid_pts = market_yield + premium − inflation                     (clamped 0.5–60, §4)
```

All debt is real, so the government's real cost is the nominal yield it pays minus the
inflation that *occurs*. The policy rate is **nominal** — it already contains the central
bank's allowance for inflation — so expected inflation must not be added on top of it (an
earlier draft did: `policy + premium + expected − π` made a perfectly managed fiat country
at π = 2 pay 2pp more than a gold country at the same real stance, forever).

What lenders add is a **floor**: they will not hold government paper yielding less than a
normal real return over the inflation they *expect*, whatever the central bank's rate is.
`era_base` — the public, long-run real rate — is used rather than the hidden neutral rate,
because rate-paid is an exact dashboard number and would otherwise leak r\*.

- **Steady state**, π = expected, policy at neutral: pays r\* + premium, in any regime.
  Gold's only edge over well-run fiat is its 1pp credibility bonus (§5.1).
- **Tight policy costs the treasury** pp for pp; loose policy saves it only down to the
  lenders' floor.
- **Only surprises erode debt.** Holding the rate under inflation works while `expected`
  lags; once it catches up the floor binds and the country pays `era_base + premium` real
  again — financial repression has a shelf life.
- **Disinflation is the hangover.** While π falls faster than `expected`, the country pays
  `era_base + (expected − π) + premium`, plus the unanchored-expectations premium (§7.6).

Worked example (simulated monthly; `era_base` = r\* = 3, premium 2, manual target,
c = 0.25) — π = expected = 2, policy 5 → pays max(5, 5) + 2 − 2 = **5%**.

- **War:** monetise at level 3 for two years with the dial left at 5. Headline reaches
  ~12.7 while `expected` lags at ~6.5 → pays max(5, 9.5) + 2 + 1.5 + 0.4 − 12.7 ≈ **0.7%**.
  Three points of GDP a year in extra minting, and the debt nearly free.
  *(**As shipped this line simulates to ≈0.61%**, not 0.7%. Step 5 runs before step 6
  (ruling P5), so the unanchored premium is priced off **last** month's expectations: 0.307
  rather than the same-month 0.375. Exactly: 9.4972 + 0.5 + 3.3070 − 12.6926 = 0.6116. The
  one-month lag is worth about 0.07pp here, and the harness header quotes 0.61 for that
  reason — §0.4 checklist 24.)*
- **Peace, disinflating** (handed to the price-stability mandate): the policy rate has to
  climb past π + r\* — it peaks near **17%** three years after the war — and rate paid
  peaks near **12%**. Inflation is back under 4% only ~7 years after the war; rate paid
  averages **~6.9%** over the 15 post-war years against 5% before it, through a
  policy-induced downturn. A target of 10 would *not* have done it: with π ≈ 10 the real
  rate is ~0, still loose. With CBI-grade credibility the same disinflation is ~2 years
  shorter and ~0.6pp cheaper — but CBI forbade the monetisation.
- **Peace, never disinflating** (dial left at 5): rate paid averages **~5.4%** — never
  below the pre-war 5% once expectations catch up — while inflation sits at 12% and climbs
  to 18% over twenty years, deep in the §9.2 *High* band.

That is the tradeoff: a cheap war now, then either an expensive peace or a permanently
inflationary one.

**The path that must not pay: never disinflating.** Under *accelerating* inflation adaptive
expectations trail π indefinitely, so the erosion term never turns positive. A reviewer's
simulation of the earlier formula showed the cheapest line was to ride inflation to 50%
and take the currency reform: rate paid at or below its pre-war level for eight years with
the dial untouched. On the revised equations the lag is ~1pp and the **tuning invariant**
holds — rate paid on the never-disinflate path stays *above* the pre-war baseline — because:

1. the unanchored-expectations premium (§7.6): 0.25pp per pp beyond the 3pp tolerance is
   already +3.75pp at `expected` = 20;
2. the §9.2 bands, including the collapse of minting income;
3. the lenders' floor, which removes the *level* gain and leaves only the lag.

In *rate-paid* terms never disinflating is still cheaper than a Volcker disinflation
(~5.4% against ~6.9%). That is acceptable — even realistic — **only because the §9.2 bands
make a standing 12–18% inflation worse overall**; they are the deterrent and must be sized
for it. Test all of this on the accelerating path, not just at steady states (§19).

---

## 11. Monetisation and QE (phase 2)

**What minting already is.** Vanilla minting *is* seigniorage — its concept text says money
can be minted "without compromising the economy". Weekly minting = 500 (`base_values`) +
GDP/1000 (the `country_gdp` code modifier, **capped at GDP 200M** by
`COUNTRY_GDP_MODIFIER_MAX_MULTIPLIER`) + gold-mine PMs, all × (1 + `country_minting_mult`).
That is ≈ **5.2% of GDP a year** up to the cap, a flat ~£10.4M a year beyond it. **The
line for every later author: baseline minting is non-inflationary seigniorage; monetisation
is the excess.**

**Monetise the deficit** — a 0–3 stepper (same widget shape as the target). Requires fiat or
digital currency, a national bank, **not** CBI.

- Each level: `country_minting_add` worth **1% of annual GDP per year** (scaled static
  modifier) — about +20% of baseline minting — for +2.5pp inflation pressure (§9.1) and
  +0.5pp cyclical premium. (A first draft used 0.25%: half of what merely enacting fiat
  yields for free, so nobody would have pulled it for the revenue. WWI-scale money finance
  ran to several % of GDP; level 3 is 3%.) Per unit of financing it is ~8× as inflationary
  as a bond-financed deficit — that ratio is the tuning knob.
- **Owner decision hiding here:** a GDP-scaled `_add` (chosen) grows with the economy and,
  past the 200M cap, to many times baseline minting. The alternative, `country_minting_mult`
  +0.2 per level, needs no GDP-scaled refresh and reads naturally in the budget tooltip
  ("Monetisation +60%"), but shrinks toward nothing relative to GDP in the late eras —
  exactly when this system is supposed to matter.
- The real decision is war finance and the §10 "inflate it away" strategy.

**Reconcile the existing minting-flavoured content in phase 2.** `monpol_currency_stability`
/ `monpol_currency_devaluation` (±GDP-scaled `country_minting_add`, applied six times in
`events/extra_law_events.txt`, including *The Printing Press of Money* and #40
*Hyperinflation Panic*) do not touch interest and so are absent from §7.5 — but once
inflation exists, a "devaluation" that only trims minting and a "hyperinflation panic"
unconnected to `te_inflation` will read as bugs. Give the pair a
`country_inflation_pressure_add` field and gate or retitle #40.

> **As shipped (§0.4, T4).** The field could not go on the pair itself: all six sites apply
> them with `multiplier = sv_money_flow_event_small`, and the engine scales *every* field of
> a modifier — a 1pp pressure field would have become thousands of points. Two **unscaled**
> companions, `monpol_currency_stability_pressure` (−1.0pp) and
> `monpol_currency_devaluation_pressure` (+1.0pp), are granted beside the originals at all
> six sites instead. #40 was **retitled** — it is now *"The Spectre of Runaway Prices"*, not
> *Hyperinflation Panic* — rather than gated: it fires while the country is *enacting*
> `law_fiat_currency`, so a `te_inflation >= 20` gate would have been near-unreachable, and
> the event was always an anticipation rather than an observation.

**Open-market operations → QE.** `cb_open_market_ops` survives with its tech gate
(`country_can_use_open_market_ops_bool`, `era_6.txt:177`), law lock, 4 intervention points
and treasury cost. Changes:

- `possible`: the rate-hike exclusion (`banking_policy_triggers.txt:25`) becomes
  `var:te_policy_rate <= 0.01` — **usable only at the floor**.
- Effect: keeps momentum +0.35 and services +5%; bubble +0.8 → **+1.5**; adds +1.0pp
  inflation pressure (§9.1); the interest field is deleted.
- AI weights rewritten: use at the floor in recession or deflation.
- Under digital currency the floor is −3%, so QE arrives later — negative rates substitute.

`cb_policy_rate_hike` / `cb_disable_policy_rate_hike` are **deleted** (§18).

---

## 12. World rate, gold, and the peg (phase 3)

### 12.1 World rate

`global_var:te_world_rate` is a **real** rate: the GDP-weighted mean of
`te_policy_rate − te_inflation_expected` over great powers whose rate is **discretionary**
— they have a dial (§4) **and** are not delegated to peg defence. **Fallback: `era_base`**
whenever no GP qualifies, when `has_global_variable` is false, and throughout phases 1–2.

Discretionary-only is what keeps it from being circular. In 1836 Britain is on gold, and
an AI Britain is on peg defence — whose target *is* the world rate; France and Austria
have national banks but are on commodity money, so since §0.6 they hold a dial confined to
`world − 1 … + 3`, a band measured from the number being averaged. Averaging all three
would define the world rate in terms of itself (and, before §0.6, ratchet it up by the
bankless spread every month). So a **narrow** dial is excluded alongside peg defence:
`te_mon_rate_is_discretionary` asks for a dial that is neither. With none of them
discretionary the world rate is `era_base` — until a player Britain takes the dial, or a
fiat great power appears, and starts moving it for everyone else.

It is real because capital responds to real returns: a fiat GP at 10% inflation and a 13%
policy rate must not force gold countries to 13%. A gold country's gap is
`policy − world` directly (its expected inflation is 0); a no-dial country pays
`world + own expected inflation + 1`; a commodity-money country with a bank pays what it
set, from a point under `world` to three over.

Computed on the global `on_monthly_pulse` with two accumulator globals (Σ gdp/10⁶ × real
rate, Σ gdp/10⁶ — the scaling is fixed-point headroom), seeded in `te_init_global_state`
(`common/on_actions/extra_on_actions.txt:22-31`).

Effect: a small country is pulled around by the hegemon's central bank.

**Phase 4 adds a sibling**, `global_var:te_world_inflation` — GDP-weighted
`te_inflation_expected` over *all* great powers, fallback 0 — computed in the same pulse
with its own accumulator pair and the same own-share exclusion (§15.1).

### 12.2 Gold flows

Gold-standard countries with a national bank only:

```
gap  = clamp( policy_rate − world_rate , −5 , +5 )
flow = gap × 0.002 × gdp          per month; positive = inflow
```

(Phase 4: `gap` is multiplied by `controls_damp` = 0.25 under capital controls — §15.4.)

**Inflows are hot money, not income.** Unqualified, a player on gold targeting world + 5
would collect ~12% of GDP a year through `add_treasury` — no counterparty, invisible in the
budget, and the only cost a tight stance. Bank Rate attracted short-term capital that
*left again*. So:

- Every net inflow is recorded in `te_gold_hot_money`. When the gap falls to ≤ 0 that
  balance leaves **first**, at twice the normal outflow speed, before ordinary drain starts.
  Attracting gold is borrowing it.
- Inflows stop once `scaled_gold_reserves ≥ 1`: a high rate can *refill* reserves to the
  limit, never stack a war chest.
- Hot money adds nothing to peg confidence (§12.3).
- **Price–specie flow closes the loop:** gold flows feed §9.1 — inflows add inflation
  pressure, outflows subtract it (0.5pp per 1% of GDP per year). A country pulling gold in
  inflates, loses competitiveness and wants a lower rate; one bleeding gold deflates its
  way back. This is how the real mechanism self-corrected, and it couples the peg to
  inflation without new state. The reserve cap alone would only stop a hoarder — a player
  who *spends* the inflow stays under the limit — so the hot-money balance is what actually
  closes the exploit.

Applied with **`add_treasury`** from the monthly country update — **not** a scaled
`country_expenses_add`. The sign argument: an expense modifier feeds `total_expenses`,
which the mod's own fiscal-stimulus reader and the §9 deficit driver both read, so a gold
*outflow* would register as deficit spending — stimulus and inflation — the wrong sign
twice. It would also distort the AI's budgeting.

Sizing: the vanilla reserve limit is 0.2 × annual GDP (`GOLD_RESERVE_LIMIT_FACTOR`), so
1pp of gap moves ~1% of the limit per month and a 2pp gap empties full reserves in about
four years. That is 2.4% of GDP per year per pp — **sanity-check it against typical Vic3
government revenue / GDP before tuning**; if revenue is ~20% of GDP, a 2pp gap costs about
a quarter of it, which is already severe. (The `scaled_gold_reserves ≥ 1` cap makes the
engine's diminishing returns moot; VERIFY IN-GAME anyway for a one-off `add_treasury`.) Show the monthly flow on the dashboard — `add_treasury` never appears in
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
| **Devalue the peg** | one-off gold reserve revaluation + export boost (`te_mon_peg_devalued`, ±0.15 over five decaying years — ruling Q12; from phase 4 it *is* `te_fx_index` set to 88 and returning at 1/30, tuned to the same peak and impulse — §15.2); confidence reset to 50; infamy and GP relations (the costs the old *Devalue* button carried); expected inflation +3 |

This absorbs banking event 12 ("Gold Standard Pressure") and the gold-peg-defence event at
`events/banking_cycle_events.txt:1510-1548`. **As shipped:** those line numbers were event
12's own first two options, so "both" were one event; it is deleted, with its draw in
`banking_cycle_effects.txt` and its loc, and its flavour text lives on as `te_peg.1.f`.

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

**Regime laws gain stances.** ~~`lawgroup_monetary_policy` is the only economy law group with
`ideological_opinion_impact = 0`.~~ **Corrected 2026-09-20:** it is not the only one —
vanilla's own `lawgroup_colonization` and the mod's `lawgroup_national_bank` are both
`economy` groups at 0 as well — and, more importantly, that field is the wrong lever. It
multiplies the **legitimacy** penalty when governing IGs disagree over the enacted law
(`vanilla_politics_reference.md` §2.4); the IG *approval* this section wants runs off
`IG_APPROVAL_FROM_LAW` / `IG_APPROVAL_FROM_LAW_CHANGE`, which it does not gate. So the
stances bite with the field left at 0, and it was left at 0. That reading is inferred from
the define names, not observed — **§0.4 checklist 17** is the in-game confirmation, and the
fallback if it fails is to set the group to 0.25 like the mod's other economy groups.

Proposed direction: hard money (commodity, gold) endorsed by Landowners and Petite
Bourgeoisie, opposed by Rural Folk and Trade Unions (*Cross of Gold*); fiat endorsed by
Trade Unions, Rural Folk and Intelligentsia; CBI endorsed by Industrialists and Petite
Bourgeoisie. Stances go through the generator input `ideology_modifications.py` — **never
hand-edit `common/ideologies/modified.txt`** (`docs/auto_generated_files.md`).

**Delivered (phase 2).** Scored `strongly_approve` +2 … `strongly_disapprove` −2 and summed
over each IG's baseline `ideologies` block — an IG holds several at once, so they net:

| IG | commodity | gold | fiat | digital | crypto |
|---|---|---|---|---|---|
| Landowners | 0 | **+2** | −2 | −2 | −2 |
| Petite Bourgeoisie | −1 | **+2** | −1 | 0 | −3 |
| Armed Forces | 0 | **+1** | −1 | −1 | −1 |
| Rural Folk | −2 | **−1** | +1 | +1 | −3 |
| Trade Unions | −2 | **−2** | +2 | +2 | −2 |
| Intelligentsia | −1 | 0 | +1 | +2 | −1 |
| Industrialists | −1 | 0 | +1 | +2 | −1 |
| Devout | 0 | 0 | 0 | 0 | 0 |

Three things that table records rather than proposes. **Landowners' hard money is gold-only**
— the shared `simple_currency` list is *neutral* on `law_commodity_money`, so the IG this
section casts as the hard-money constituency has no opinion about the regime every country
starts on. **The Armed Forces gained a modest hard-money lean** as a side effect of putting
`simple_currency` on `ideology_patriotic` to un-dilute the Petite Bourgeoisie; it was
accepted rather than worked around, because an officer corps on fixed salaries and pensions
is the classic sound-money constituency and the *Inflation ≥ 8%* row above already puts them
on the losing side. Two pre-existing stances had to be worked around at all: CBI-era mod
content already put `simple_currency` on `ideology_particularist` (which cancelled the Cross
of Gold on `ideology_agrarian` exactly) and `advanced_curency` on `ideology_meritocratic`
(which left the Petite Bourgeoisie pro-digital); both were left untouched and the direction
was landed by **adding** a stance to a free baseline instead — `ideology_isolationist` for
Rural Folk, `ideology_patriotic` for the Petite Bourgeoisie (§0.4, T7).

**Side effect worth watching in a long AI run.** The AI's *ideal law* per group is derived
from its governing IGs' ideologies, and until now `lawgroup_monetary_policy` had stances from
four ideologies only. AI countries may now actively pursue monetary law changes to match
their coalition, on top of the mod's own `ai_enact_weight_modifier` ladder (gold 100, fiat
200, digital 300, crypto 50) — so monetary laws may change more often than before, and P9's
"dollarisation clears on the next `lawgroup_monetary_policy` enactment" path fires more
readily as a result. Two mechanisms checked and *not* affected: political movements (vanilla
movements are explicit entities with their own `creation_trigger`; none forms around a law
group), and regime change (`lawgroup_monetary_policy` already carried
`affected_by_regime_change = yes`, and a regime change imposes the winner's law regardless of
anyone's stance). Note also vanilla's global `MAX_IG_APPROVAL_FROM_LAWS` ±5 cap across all
law groups: for an IG already pinned by the rest of the statute book, these standing ±1 rows
are absorbed and only the one-off enactment swing lands.

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

## 15. Exchange rates and the trilemma (phase 4)

> **Read with §0.5 "The bank's own reserve" in hand.** This section and §15A were rebased on
> phase 3 as it stood *before* the owner moved gold out of the treasury (they came in through
> PR #340, cut from the phase-3 branch mid-playtest). Since then gold flows move
> **`te_bank_gold`**, the central bank's own vault, never the treasury: wherever the text below
> says "reserves" in a gold or peg context — the FX-support AI weight's "reserves < 0.3", the
> swap line's effect on the hot-money exit — read `te_mon_bank_gold_scaled`, not
> `scaled_gold_reserves`; and a swap line or lender-of-last-resort article that *lends gold*
> should credit the vault (the recapitalisation path), not `add_treasury`. Nothing else in the
> phase 4/5 design depends on which stock the gold sits in.

> **Scoped 2026-09-20** from a second owner interview plus a file survey of the FX buttons,
> the trade modifier types and the §9.3 cost-push code, then **revised the same day after a
> review on PR #340** that cross-checked it against phase 3 *as shipped*. The baseline is
> therefore [§0.5](#05-phase-3-as-shipped--rulings-deviations-and-open-checks), not §12 as
> first drafted — in particular decision **H** (nobody faces a world rate that contains
> itself), rulings **Q4** (`te_mon_is_on_gold` / `te_mon_is_metallic` are the only regime
> tests), **Q10** (confidence heal and crisis cooldown) and **Q12** (Devalue's shipped export
> boost). **Owner decisions:** the capital-controls politics (already recorded here before the
> scoping pass); **`te_fx_index` is displayed exactly**; a **declared non-gold peg is a
> treaty article, not a law** — so it belongs to phase 5a (§15A.2), and phase 4 ships only the
> float, the metallic par and capital controls. The design below was approved by the owner as
> a whole; individual numbers and rules the owner did not single out stay marked
> **(proposed)**, and every number is a §21 tuning constant.

Organising idea: the **policy trilemma** — pick two of a fixed exchange rate, free capital
flows, an independent rate.

| Corner | In the mod | Result |
|---|---|---|
| Peg + open capital | gold standard (§12); from phase 5, any **anchored** country (§15A) | rate must track the world rate / the anchor's rate |
| Float + open capital | fiat / digital | free rate; the **exchange rate is an outcome** of the rate gap and the inflation gap. Weak = export edge + imported inflation; strong = the reverse |
| Peg + capital controls | gold or an anchor, plus `cb_capital_controls_outflow` | independent rate *and* a peg, at an efficiency and political cost (§15.4) |

### 15.1 `te_fx_index` — definition and monthly update

`te_fx_index` is a country variable, **100 = par, clamped 50–150**. By §2 fact 2 there is no
price level, so it can only be a **real** exchange rate: it says how cheap the country's
goods and assets are to foreigners, never how many francs buy a pound.

```
fx_target = 100
          + 4.0 × clamp( own_real_rate − world_rate , −5 , +5 ) × controls_damp     carry / capital flows
          − 2.0 × clamp( expected − world_inflation , −10 , +10 )                   confidence in the currency
          − 1.5 × max( 0 , cyclical_premium )                                       flight from a distressed sovereign
          + te_fx_shock                                                             events; decays 1/12 per month

te_fx_index += (1/12) × ( fx_target − te_fx_index )          ~1-year adjustment; then clamp 50–150
```

- `own_real_rate = te_policy_rate − te_inflation_expected`; `world_rate` is the country's
  own per-pulse copy **`te_mon_world_rate_now`**, already real and — by decision H (§0.5) —
  **with the country's own share subtracted**. That matters here more than anywhere: read
  against the raw global, the carry term would be structurally zero for the hegemon, the one
  country whose currency should dominate the system. A player Britain's hike moves sterling.
- **`global_var:te_world_inflation` is new**: the GDP-weighted mean of
  `te_inflation_expected` over **all** great powers (inflation is not circular the way the
  world *rate* is, so no discretionary-only filter), fallback **0**, built exactly like the
  world rate — accumulator pair in the global pulse, a per-country copy with the **own share
  excluded** (`te_mon_world_inflation_now`), seeded in `te_init_global_state`.
- **The formula runs for every country as `te_fx_shadow`**, whatever its regime; §15.2 says
  which countries' *index* follows it. `te_mon_overvaluation = max(0, te_fx_index −
  te_fx_shadow)` is therefore a phase-4 quantity, not a phase-5 one.
- The inflation term looks double-counted against the real-rate term (which already
  subtracts `expected`) and is not: the first is the return on holding the currency, the
  second is whether anyone trusts it. A country at 12% policy and 10% expected inflation has
  a healthy real rate and a weak currency.
- `controls_damp` = **0.25** while `banking_capital_controls_out` is active, else 1 (§15.4).
- `te_fx_shock` is the only event-writable input: events never `set_variable` the index
  (two documented exceptions: §12.3's *Devalue*, which is *defined* as a jump, and the §18.2
  save migration). Clamped ±40, multiplied by 11/12 each month. **A shock delivers 38% of its
  nominal size**: it decays at the speed the index adjusts, so the index never catches it —
  `x_n = (n·S/11)·(11/12)ⁿ`, peaking at month ~11 at 0.384 × S. Every shock in §15.5 is sized
  knowing that (a nominal −26 is a 10-point move); the ±40 clamp caps any event at ~15 points,
  so nothing but *Devalue* and policy can reproduce a devaluation.
- **Seed at 100** behind `has_variable`; never removed (it backs a multiplier — §16.2).

**Projection (the evidence for the two speeds).** Target displacement is
`4 × gap` for a real-rate gap and `2 × gap` for an inflation gap; the index closes
1 − (11/12)ⁿ of it after n months — 41% at 6, 65% at 12, 88% at 24.

| Sustained condition | Target | Index at 6 mo | 12 mo | 24 mo | Export edge at 24 mo |
|---|---|---|---|---|---|
| 2pp loose (real-rate gap −2) | 92 | 96.7 | 94.8 | 93.0 | +8.8% |
| 5pp loose (clamp) | 80 | 91.8 | 87.0 | 82.4 | +22% |
| 5pp inflation gap, neutral real rate | 90 | 95.9 | 93.5 | 91.2 | +11% |
| 5pp loose **and** 10pp inflation gap | 60 | 83.6 | 74.0 | 64.8 | +44% |
| Hyperinflation (both clamps, premium +10) | 45 → floor 50 | 77.6 | 64.4 | 51.8 | +60% |

So a routine stance difference is worth a single-digit trade edge, the deleted *Devalue*
button's ±25% (§15.3) takes a maximal stance gap held for about two years, and only a
currency crisis reaches the floor.

### 15.2 Regime rules

Keyed on phase 3's triggers, **never on raw law names** (ruling Q4: a missed raw
`law_gold_standard` test is silent). `te_mon_is_metallic` is already `te_mon_is_on_gold OR
law_commodity_money` and already suspension-aware, so *Suspend convertibility → floats* needs
no branch of its own.

| Case | `te_fx_index` |
|---|---|
| `te_mon_is_metallic = yes` | **par, 100** — the *nominal* parity is fixed, so there is no trade edge to give. The shadow still runs (below) |
| …after §12.3 *Devalue the peg* | set to **88**, returning to par at **1/30** a month while `te_fx_devalued_months` (set to 60 by the option) is > 0. This **replaces** ruling Q12's `te_mon_peg_devalued` (±0.15, five decaying years) and is tuned to match it: same ±0.15 peak (12 points × 1.25%), same total impulse (0.15 × 30 months ≈ 0.375 advantage-years), half gone at 21 months against 30. The modifier is retired through `legacy_modifier_cleanup.txt` |
| Anchored (phase 5, §15A) | the anchor's index |
| `law_command_economy` | par; excluded, like §14's other exclusions (inconvertible currency). No shadow |
| Everything else — fiat, digital, crypto, dollarised, a suspended gold standard; with or without a national bank | `te_fx_index = te_fx_shadow`. For the no-dial cases the rate term is **zero** (§0.7 ruling F1 — the first draft's "pinned near +1, the bankless spread" would have parked every bankless floater four points strong), so the index is driven by the inflation gap, the premium and shocks |

**The metallic shadow — real appreciation under a fixed parity.** "Convertibility *is* the
exchange rate" is true of the nominal rate only, and the real rate under a fixed nominal peg
is where the history lives: inflate at home, price yourself out, lose the peg. So a metallic
country's shadow runs too, with one substitution — ruling Q12 pins `te_inflation_expected`
to 0 under metal, which would leave both inflation-bearing terms structurally dead exactly
where they are needed, so the metallic shadow reads **realised core inflation**
(`te_inflation_core`) in both places. That input already contains §12.2's price–specie term,
which closes the classical loop with no new state: gold inflow → price–specie pressure →
inflation → shadow falls → overvaluation → confidence drains → the inflow's purpose is
defeated. The sign flip between regimes falls out by construction: under a float high
inflation lowers the index; under a peg the index cannot move, so the same inflation shows up
as overvaluation.

**Overvaluation drains the gold peg**, as a fifth §12.3 term beside the rate-gap drain
(adding to it, not replacing it): **−1 confidence per 2 points of `te_mon_overvaluation`
beyond 5, per month, × `controls_damp`**. Set against ruling Q10 rather than against zero:
overvaluation > 5 counts as *under pressure*, so the +1 heal holds instead of netting the
drain away, and a crisis it triggers inherits Q10's 24-month cooldown. Phase 5a's
`currency_peg` reuses this term unchanged — phases 4 and 5 run on one mechanism.

### 15.3 Consequences

**Two fixed-sign scaled modifiers**, not one signed one — §17 check 8 (a negative
`multiplier`) is still open:

| Modifier | Multiplier | Per point |
|---|---|---|
| `te_fx_weak` | `max(0, 100 − te_fx_index)` | `state_export_advantage_mult = 0.0125`, `state_import_advantage_mult = -0.0125` |
| `te_fx_strong` | `max(0, te_fx_index − 100)` | `state_export_advantage_mult = -0.0125`, `state_import_advantage_mult = 0.0125` |

- Both are **country-scope** static modifiers carrying `state_*` fields, which propagate to
  every owned state — the shape vanilla laws use and `banking_fx_devaluation` already used
  from JE scope. No per-state loop. Re-applied once, from the monthly country update (one
  refresh site), always both, a zero multiplier on the inactive one.
- **Calibration anchor:** the deleted `banking_fx_devaluation` / `banking_fx_support` gave
  ±0.25 on exactly these two types. 0.0125 per point reproduces that at index 80 / 120 —
  the new system's *large* move equals the old system's *button press*, and the floor (50)
  is 2.5× it. These would be the first trade modifiers in the mod applied with the scaled
  `multiplier =` pattern; `state_export_advantage_mult` / `state_import_advantage_mult` are
  vanilla types and need no registration.
- **Foreign-currency debt:** a weak currency adds **+0.05pp of cyclical premium per point
  below par** (index 80 → +1pp) — `te_mon_premium_fx`, a sibling of
  `te_mon_premium_unanchored` in step 5. It is inside the premium, so it also feeds back
  into `fx_target`'s third term; that loop has gain 1.5 × 0.05 = 0.075 and converges.
- **Imported inflation is a change term, not a level** — the §9.3 rule ("only *changes* are
  inflationary") applies to the currency too: a currency that has been 20% weak for a decade
  is a fact about that world. Mirror §9.3 exactly:

  ```
  imported   = 0.15 × ( te_fx_avg − te_fx_index )            pp; weak vs. its own average = positive
  te_fx_avg += (1/36) × ( te_fx_index − te_fx_avg )
  cost_push  = clamp( basket term + imported , −6 , +6 )     ONE clamp, shared with §9.3
  ```

  Added **inside** the `te_cost_push` value block (`te_monetary_effects.txt`, step 6a) so it
  shares the ±6pp clamp, reaches core only through expectations, and is looked through by
  the mandates exactly as a grain shock is. A 20-point depreciation lifts headline ~3pp,
  fading over three years. `te_cost_push` is force-zeroed at three sites (no market, the
  command / repressed path, the reset effect) — **the imported term must be zeroed at the
  same three**. **`k` is banded by trade openness**, because the currency's *upside* already
  is — `state_export_advantage_mult` pays in proportion to how much a country trades, so a
  flat pass-through would give an autarkic continental power an entrepôt's downside.
  `market_trade_reliance` (market scope, no target = share of orders due to world-market
  trade) is a comparison trigger, not a value, so it buys three bands on the market §9.3
  already resolves: **×0.6 / ×1.0 / ×1.5** at reliance < 0.1 / 0.1–0.3 / > 0.3 **(proposed;
  §17 check 20 — the trigger has no vanilla script use)**. Seed `te_fx_avg` to the first observation; **re-seed it whenever the anchor
  changes** (§15A.1), for the same reason §9.3 re-seeds on a market change.
- No momentum / bubble terms. The deleted modifiers carried them, but the stance already
  delivers stimulus (§8) and the trade edge is the FX channel's own; adding both would
  count a loose stance twice.

### 15.4 Capital controls

`cb_capital_controls_outflow` and its static modifier survive, and gain the mechanic that
makes them the trilemma's third corner. While `banking_capital_controls_out` is active,
**`controls_damp = 0.25`** multiplies:

1. the rate term of `fx_target` (§15.1);
2. §12.2's gold-flow `gap` — so a gold country can hold a rate 4pp off the world rate and
   bleed as if it were 1pp off;
3. §12.3's confidence drain "per pp of negative gap" (and, in phase 5, the overvaluation
   drain on an anchored country).

It does **not** damp the inflation or premium terms: controls stop capital leaving, not
the currency being distrusted.

**The price (owner decision, now with numbers — the numbers are (proposed)).**
`te_capital_controls_months` counts months the modifier is held **outside a crisis**.
"Crisis" is one shared trigger, `te_mon_in_external_crisis` — banking panic or downturn, at
war, a §12.3 peg crisis (confidence ≤ 40 or the crisis event pending — deliberately above
the event's own ≤ 20, so emergency controls are forgiven *before* the crisis breaks), or the §9.2
hyperinflation band — reused by the AI weights below so the two cannot drift apart.

| Counter effect | Rule |
|---|---|
| Industrialists, Petite Bourgeoisie | −1 approval per 12 months, to **−5** at five years — "major if prolonged" |
| Trade Unions | flat **+1** while controls are on (Bretton-Woods-era labour backed them) |
| Investment-pool drag | `state_capitalists_investment_pool_efficiency_mult` −0.02 per 12 months, to −0.10. **Replaces** the modifier's current `state_capitalists_investment_pool_contribution_add = 0.05`, which made trapping capital a *bonus* |
| In a crisis | counter **frozen**, neither growing nor decaying — emergency controls are forgiven. **Freeze wins over decay:** controls lifted *during* a crisis do not start decaying until it ends, or lifting in a panic banks free decay |
| Lifted | counter **decays 3 per month** (a five-year stint clears in 20 months). Deviation from the original wording ("resets when lifted"), which a one-month toggle would exploit |

One scaled modifier (`te_capital_controls_fatigue`, multiplier = counter ÷ 12 clamped 0–5)
applied from the monthly country update; the Trade Union +1 rides on
`banking_capital_controls_out` itself. The modifier's existing bureaucracy, influence,
authority, momentum and bubble fields stay.

### 15.5 Deletions, re-pointing, UI, AI

**`cb_fx_devaluation` and `cb_fx_support` dissolve — delete them as a pair.** They are
mutually exclusive in `possible` and each disable-button's `ai_chance` reads the other's
modifier, so deleting one leaves dangling references. Devaluing is the §12.3 crisis option
under a peg and an outcome of loose policy under a float; "support" is a tight stance.
Footprint: §18.2. `cb_fx_swap_lines` survives phase 4 **unchanged** and is replaced by a
treaty article in phase 5a.

Re-pointing the FX-flavoured event content (all via `te_fx_shock`, never the index):

| Site | Today | Phase 4 |
|---|---|---|
| `banking_cycle_events.58` "End the Gold Standard" | `banking_event_managed_devaluation` | shock **−26** (a ~10-point move — §15.1's 38% rule); modifier kept (its throughput / prestige fields are not FX) |
| `banking_cycle_events.12` "Gold Standard Pressure" | same modifier | already absorbed by §12.3 in phase 3 — nothing here |
| five `banking_event_fx_defense` sites | expense-scaled modifier | + shock **+13** (~5 points; a defence that works props the currency) |
| `monpol_currency_devaluation` law-event pair | minting / pressure | + shock **−13** (~5 points) |
| `banking_crash_intervention_suspend_convertibility` | `state_export_advantage_mult = -0.10` | field removed — the float now produces the export effect, with the right sign |
| `te_mon_peg_devalued` (ruling Q12, `te_peg.1`) | ±0.15, five decaying years | retired — the option sets the index to 88 instead (§15.2) |

**UI.** One dashboard row under the phase-1 Monetary Policy block: the index, exact, one
decimal, with a breakdown tooltip listing the four `fx_target` terms, the target, and
`controls_damp` when it bites; a second line shows the resulting trade edge and imported
inflation. Add `te_fx_index` to the history store (§16.4) — the chart is the loop detector
for §20 risk 9. Nothing here is hidden state: every input is already exact on the
dashboard, so exact display leaks nothing (r\* enters only through the policy rate the
player chose). Gold / commodity countries see "Par (convertible)".

**AI.** No FX tool remains to weigh, only capital controls. `cb_capital_controls_outflow`
`ai_chance`: strongly positive when `te_mon_in_external_crisis = yes` **and** (index < 85,
or gold flow negative with reserves < 0.3, or peg confidence ≤ 40 — the same threshold); its disable side
strongly positive when not in crisis, rising with `te_capital_controls_months`. The
`banking_stance_is_tight` easing weight on the deleted `cb_fx_support` (§0.2's possibly
sign-wrong note) is deleted with it, which closes that item.

### 15.6 Open after scoping

- Whether overvaluation under a peg should also cost trade directly (a share of it counted
  into `te_fx_strong`): real appreciation *is* lost competitiveness. Left out — the
  confidence drain already prices it, and a second consequence of one gauge is how loops get
  double-counted.
- ~~Commodity-money countries have a shadow but no `te_peg_confidence` to drain; their
  overvaluation is display-only until §0.5 decision H's parked "commodity money also moves
  gold" question is settled.~~ **Closed 2026-09-21 (§0.6 R7, issue #351):** not by moving
  gold, but by charging the *price-level half* of that overvaluation
  (`te_mon_fx_term_inflation`) as §9.1 inflation pressure. No vault, no flow variable, no
  confidence — the row is no longer display-only.
- The commodity price-specie term is **one-sided**, on `te_mon_fx_overvaluation_value`'s own
  `min = 0`: prices *below* the world's buy nothing. The mirror half — cheap prices pull
  specie in and inflate — is the other side of the real mechanism and is left out on
  purpose, because it would tether a metallic country to a **fiat** world's inflation rather
  than to a shared standard's. Worth revisiting only if a mostly-metallic world ever wants a
  common price trend (a gold rush is the §9.1 gold-supply term's job, not this one).
- `te_fx_index` as an input to migration or tourism attraction — natural, but neither
  system is touched this phase.
- Tech replacements: `keynesian_economics` and `international_exchange_standards` each lose
  a tool-unlock bool (§18.2). Candidates if the tech tooltips feel thin: a
  `country_fx_adjustment_speed_mult`-style type on the latter. Not designed.

## 15A. International monetary arrangements (phase 5)

> **Implemented 2026-09-21** — what shipped, where it departs from this section and what is
> still unverified: [§0.8](#08-phase-5-as-shipped--rulings-deviations-and-open-checks).
>
> **Reviewed 2026-09-21 for leverage, coercive variants and exploit surface — nothing
> owner-decided, findings and directions only:** [§15B](#15b-leverage-coercion-and-exploit-hardening-phase-6-proposed).
>
> **Planned 2026-09-21 as phase 6, owner rulings taken, not built:** [§15C](#15c-phase-6-plan--leverage-coercion-and-exploit-hardening-proposed-not-built).
>
> **Scoped 2026-09-20** in the same pass as §15. Owner decisions: **one "anchored" state
> underlies every arrangement**; the declared peg is a **treaty article**; all three families
> ship, **staged 5a / 5b / 5c** so each can be cut; a bloc currency's rate is **the leader's
> own dial**; bloc adoption is **neither automatic nor purely voluntary — the leader can
> exert pressure** (§15A.3). Everything else is **(proposed)**. (This section was §15.1
> "to scope"; it is renumbered 15A so §15's own subsections can be numbered. Older text that
> says "§15.1" about international arrangements means this section.)

Phases 1–4 treat every country as a monetary island apart from the world rate. Phase 5 lets
a country tie its money to another's. Design principle as elsewhere (§1): each arrangement
is a genuine tradeoff **for both parties**, and asymmetry between members comes from shared
mechanics (size, credibility, cycle position), never from special-casing.

### 15A.1 The spine: the anchored state (ships with 5a)

| Variable | Meaning |
|---|---|
| `te_mon_anchor` | **scope** variable → the anchor country. Copy the `te_basket_market_owner` contract (`te_monetary_script_values.txt:144-165`): it cannot hold 0, is read as `var:te_mon_anchor = { … }`, and is only meaningful while `te_mon_anchor_kind > 0` |
| `te_mon_anchor_kind` | 0 none · 1 treaty peg (5a) · 2 bloc currency (5b) · 3 currency board (5c). When several apply the **highest wins**: an overlord's board overrides a bloc, a bloc overrides a bilateral peg |
| `te_fx_shadow` / `te_mon_overvaluation` | **phase-4 variables** (§15.1–15.2): the float formula, run for everyone, and `max(0, index − shadow)`. An anchored country's index is its anchor's, so its overvaluation is how far it has diverged from the currency it borrowed — **the one pressure gauge all three arrangements read**, and the same one a gold peg already reads |

An anchored country (`te_mon_is_anchored`: kind > 0 and the anchor is valid):

- **has no dial.** `te_mon_has_dial` gains one line, `NOT = { te_mon_is_anchored = yes }`,
  beside the dollarised one — a single edit that propagates to every consumer (five sites
  in `te_monetary_effects.txt`, four custom-loc blocks).
- **imports the rate.** A third branch in `te_monetary_set_derived_rate`:
  `te_policy_rate = anchor's te_policy_rate + spread` — peg **0.5**, board **0.25**, bloc
  **0**. Distinct from both existing peg-ish concepts: mandate 3 is a *dial* country
  defending gold; dollarisation derives from the era base, not from anyone's rate.
- **takes the anchor's `te_fx_index`.** Its own formula runs on as `te_fx_shadow`.
- **cannot monetise or run QE** — it is not their currency to print.
- **keeps its own inflation, neutral rate, stance gap and cycle.** This is the whole point:
  the imported rate is the wrong rate whenever the two cycles diverge, the stance politics
  (§13) and the inflation bands (§9.2) bite as normal, and the country cannot devalue its
  way out. `te_mon_overvaluation` measures exactly how much it wishes it could.
- **imports credibility:** its anchor coefficient `c` (§9.1) becomes
  `max( own c , 0.8 × anchor's c )`, and expectations anchor on the *anchor's* target.

**Validity.** The anchor must itself have a dial (`te_mon_has_dial`), which also forbids
chains and cycles — an anchored country has no dial, so nobody can anchor to it. If the
anchor loses its dial (law change, command economy, itself anchored by a higher kind), the
arrangement **lapses**: kind → 0 next month, and a treaty's `requirement_to_maintain` breaks
the article.

**Detection: cheap monthly validity, event-driven discovery, yearly full scan.** There are
no bloc join / leave on-actions and no ceased-to-be-a-subject on-action, and a per-country
`any_scope_treaty × any_scope_article` walk every month for ~200 countries would be the
heaviest thing in the update, spent detecting something that happens a handful of times a
campaign. Going yearly is worse — an ex-member would import its ex-leader's rate for up to a
year. So step **1c** is split three ways:

1. **Monthly — validity of the stored pair only.** Is my anchor still dialled; am I still in
   that bloc with the bool set / still that kind of subject of it / still bound by that
   treaty (`var:te_mon_anchor = { … }` tests, no article walk). Failure → kind 0 now.
2. **Event-driven — discovery.** The articles' `on_entry_into_force` / `on_break` /
   `on_withdrawal`, `on_become_subject` and the four `released_as` hooks, the 5b adoption
   and exit actions: each calls the full recompute for the countries involved, re-rooted
   through `te_monetary_internal.1` as the release hooks already are
   (`te_monetary_on_actions.txt:204-220`) — cross-country **reads** are fine, a modifier
   **write** must run with the owner in ROOT.
3. **Yearly — the full scan** (treaty walk, bloc read, subject test, precedence), as the
   safety net for anything with no hook: a subject type changing, a bloc tier changing, a
   higher kind appearing over a lower one.

On any change of (kind, anchor): re-seed `te_fx_avg` (§15.3), re-seed `te_basket_avg` if the
market also changed, and snap `te_fx_index` to the new anchor's — or, on *leaving*, to
`te_fx_shadow` (that jump **is** the devaluation).

**Asymmetric magnitudes, shared mechanic.** Wherever a stronger party carries a weaker one,
`provider cost = recipient benefit × clamp( recipient gdp ÷ provider gdp , 0 , 1 )`. Britain
backing Belgium pays a sliver of what Belgium gains; Belgium backing Britain would pay all
of it. Because the term is GDP-scaled it cannot live in a treaty's static `source_modifier`
/ `target_modifier` block: it is one scaled modifier per role
(`te_mon_arrangement_provider`, `…_recipient`), summed over a country's arrangements and
re-applied from the monthly update. Treaty blocks carry only flat flavour (influence,
prestige).

### 15A.2 Phase 5a — treaty articles

Three directed articles. The old "to scope" sketch listed **reserve pooling** as a fourth; it is
folded into the swap line, which under gold *is* reserve lending.

| Article | Source → target | Weaker party | Stronger party |
|---|---|---|---|
| **`currency_peg`** | pegger → anchor (`required_inputs`: none beyond the target country) | anchored, kind 1: no dial, rate = anchor + 0.5, credibility import, structural premium **−0.5pp**; `te_mon_overvaluation` drains `te_peg_confidence` by §15.2's term, unchanged (so Q10's heal-holds-under-pressure and 24-month cooldown apply) | "reserve currency": structural premium −0.1pp per 5% of world GDP pegged to it, cap −0.5; small influence upkeep. No obligation — a bare peg is unilateral in substance, which is why it is cheap to grant |
| **`swap_line`** | provider → recipient | peg confidence **+2 / month**; cyclical premium **−1pp**; in a panic, its §12.2 hot-money exit runs at ×1 instead of ×2 | GDP-scaled share of that premium cut as a premium **rise**; while the recipient is in `te_mon_in_external_crisis`, a treasury draw of 0.1% of *recipient* GDP a month |
| **`lender_of_last_resort`** | guarantor → ward | §7.6 debt-load premium **halved**; `banking_cycle` panic severity inputs reduced | GDP-scaled share of the halved premium; **on the ward's default**, an event: *honour* (pay 5% of ward GDP, keep the article) or *renege* (article breaks, prestige and infamy cost, every other ward's benefit suspended for five years — guarantees are only worth the last one honoured) |

- **Peg crisis.** At `te_peg_confidence ≤ 20` the §12.3 event fires for a kind-1 country with
  the options re-read: **Defend** (capital controls forced on for a year, confidence +40 —
  the pegger has no rate to raise); **Break the peg** (withdraw from the article; index
  snaps to shadow; premium +2pp for 5 years); **Re-peg lower** (stay; `te_fx_shock`-style
  one-off that re-bases the country's *shadow* upward by half the overvaluation — a
  negotiated devaluation — infamy and anchor relations cost).
- **Gating.** **Tech (owner decision 2026-09-21, replacing `central_banking` on all three):**
  `currency_peg` at `international_exchange_standards`, `swap_line` at `macroeconomics`,
  `lender_of_last_resort` at `intergovernmental_organizations` — the declared peg is a
  gold-standard-era arrangement, the swap line a 20th-century instrument, the guarantee the
  Bretton Woods idea, so the toolkit arrives over three eras instead of all at once. All three
  are also hidden entirely under `banking_system_simplified` (§0.9).
  `currency_peg`: source has no higher-kind anchor, target `te_mon_has_dial` and
  is a great or major power or the source's market owner; mutually exclusive with a second
  peg. `swap_line` / `lender_of_last_resort`: provider has a national bank and outranks or
  out-GDPs the recipient. Same-draft conflict checks go in **`can_ratify`**, never
  `possible` (`scope:treaty` is unpopulated there — `scripting_best_practices.md:2502-2506`);
  exclusions symmetric. `on_entry_into_force` runs with the **article** in ROOT — it calls the
  anchor-refresh through the re-rooting event and does nothing else; the monthly compare is
  the source of truth.
- **Reading treaties from the pulse:** `any_scope_treaty = { binds = X any_scope_article = {
  has_type = Y } }` (in-force treaties only). Do not lift `no_duplicate_treaty_article`
  verbatim — its `scope:treaty` guard only resolves in `can_ratify`.
- **AI.** Wide gate, continuous tilt, **every score line tagged `desc =`**. Pegging scores up
  with economic dependence on the target, a shared market, low own credibility, high own
  inflation; down with a diverging cycle and rivalry. Providers score up with influence
  goals, a shared bloc and the recipient's trade share; down with the GDP-scaled cost and the
  recipient's `scaled_debt`.
- **`cb_fx_swap_lines` is deleted here** (button, disable-button, sgui pair, widget rows,
  `banking_fx_swap_lines`, its tech bool and law lock — the §18.2 recipe again). Its
  anonymous "−5 relations with every GP" becomes a named counterparty with a real cost.
- Swap lines lending peg confidence — §15's old open question — is answered **yes**, above.

### 15A.3 Phase 5b — power-bloc shared currency

A new principle group, `principle_group_monetary_union`, three tiers. **Tiers do not stack:
each restates the full list.** No finance-flavoured principle exists in vanilla or the mod,
so the slot is free.

| Tier | Grants |
|---|---|
| **1 — Monetary cooperation** | `member_modifier`: every member gets the `swap_line` recipient effect from the leader at half strength, the leader the GDP-scaled cost. No anchoring |
| **2 — Common currency** | tier 1 + `power_bloc_modifier`: `power_bloc_shared_currency_bool = yes` (script-only bool; vanilla's `power_bloc_allow_foreign_investment_lower_rank_bool` is the precedent). Members **may adopt** (below). Adopters: kind 2, anchor = `power_bloc.power_bloc_leader`, spread 0, credibility import; `state_trade_advantage_mult` **+0.05** (transaction costs); leader: reserve-currency premium cut as in 5a, + `power_bloc_cohesion_add` per adopter |
| **3 — Fiscal backstop** | tier 2 + the leader is `lender_of_last_resort` to every adopter (GDP-scaled cost, the honour / renege event) and adopters' overvaluation premium (below) is **halved**. The "whatever it takes" tier — what makes the union safe is what makes it expensive to lead |

- **The leader sets the rate with its own dial or mandate (owner decision).** No virtual
  bloc bank, no shadow targets. The leader keeps its dial; its costs are the backstop, the
  cohesion politics and being the named cause of every member's wrong stance. The leader
  must be fiat / digital with a dial, or the principle is inert.
- **Adoption is per member, not automatic.** Principles are bloc-wide, and "leave the whole
  bloc" is too blunt an exit. A dashboard action *Adopt the common currency*, gated on
  **convergence criteria**: fiat / digital + national bank, headline inflation within 3pp of
  the leader's, `scaled_debt < 0.5`, no higher-kind anchor. Stored as
  `te_mon_union_member = 1`; kind 2 also requires the bool and current bloc membership, so
  leaving the bloc or losing the tier ends it through the ordinary monthly compare — as an
  **exit** (below), not silently.
- **No peg to break, so the premium is the valve.** An adopter has no `te_peg_confidence`.
  Its `te_mon_overvaluation` instead feeds the cyclical premium: **+0.1pp per point beyond
  5** (halved at tier 3). A member in a slump while the bloc runs hot gets a tight stance, no
  devaluation, a rising premium and a worsening debt spiral — the euro-crisis shape, from
  nothing but the shared mechanics.
- **Convergence pressure — the leader's lever (owner requirement; mechanics proposed).** A
  leader toggle on its dashboard, *Press for monetary convergence*, carrying a static modifier
  with `country_influence_cost_add` while on (the capital-controls modifier is the
  precedent), scaled by the number of holdouts. While on, each **holdout** (a member that
  could adopt but has not):
  - loses the tier-1 cooperation benefit, and goes on missing the adopters' `+0.05` trade
    advantage — the costs of staying out are **political and access, never a premium**. (An
    earlier draft charged a "holdout premium". Struck on review: Denmark and Sweden borrowed
    more cheaply outside the euro than most members inside it, and the design's own
    euro-crisis valve argues that *losing* the dial is what raises a premium — refusing to
    lose it cannot raise one too.)
  - has the **debt criterion waived** — pressed adoption only needs the inflation criterion.
    This is how a union acquires the member that should not have joined, and why tier 3 is
    expensive;
  - faces the event *The Question of the Common Currency* **when the answer could have
    changed, not on a timer**: pressure newly applied; the convergence criteria newly met; a
    bloc tier change; a change of government in the holdout — with a floor of once per five
    years (`te_mon_union_last_asked`). A three-yearly popup with a stable answer is exactly
    the "clear right answer" §1 says to automate. **Adopt**, or **refuse**: relations with
    the leader fall, the leader loses bloc cohesion, and the holdout gains
    `country_leverage_resistance_add = 250` for ten years, refreshed not stacked (one rank
    step on vanilla's 250 / 500 / 750 / 1000 ladder). That makes holding out a *strategy*
    that builds something — a reputation for monetary independence that blunts the leader's
    leverage generally — rather than an endurance test.
  - **AI-versus-AI never fires the event**: it resolves on the adoption score directly, and
    the leader's dashboard lists holdouts with their current answer, so a human leader sees
    the cohesion cost coming instead of discovering it.

  So pressure costs the leader influence continuously and cohesion on every refusal; a bloc
  of stubborn members is cheaper left alone. AI holdouts weigh adoption on the same score as
  a 5a peg plus the forgone cooperation and trade terms; AI leaders press only with surplus
  influence and cohesion above a floor.
- **Exit is possible and expensive.** *Leave the common currency* (or leaving the bloc /
  the bloc losing tier 2): index snaps to `te_fx_shadow` (the devaluation it could not have
  inside), structural premium **+3pp decaying over ten years**, a one-off investment-pool
  hit, radicals, leader relations and cohesion loss, `te_mon_union_member = 0` with a
  ten-year re-adoption lock. Tuning invariant, checked with the harness: **exit must be worse
  than staying for at least five years** for a member at 15 points of overvaluation, and
  better thereafter — otherwise it is either never or always right.
- **Customs unions** (§15's old open question): adoption does **not** require sharing the
  leader's market, but an adopter *in* the leader's market already shares its §9.3 basket, so
  its inflation diverges less and the union is safer — optimal-currency-area theory from the
  existing market mechanic, with no rule written. The shared currency is added as one more
  crisis-transmission channel in `banking_cycle_effects.txt` beside `is_in_customs_union_with`
  (`:1845-1860`, `:1918-1927`).

### 15A.4 Phase 5c — subject currency boards

**Rule-based, not a button.** Subject types carry no modifiers and there is no
`subject_modifier` / `overlord_modifier` key, so everything is script-applied from the
monthly compare.

- A subject whose type has vanilla **`autonomy_level = 1`** — puppet, vassal, colony, crown
  land — is **automatically kind 3**, anchored to its direct overlord, spread 0.25. Script
  cannot read `autonomy_level`, so this is one scripted trigger, `te_mon_is_board_subject`,
  holding the `is_subject_type` OR-list; re-derive it from
  `common/subject_types/` on every vanilla bump. If the overlord has no dial the subject falls through to the ordinary no-dial rule.
- `autonomy_level = 2` types (dominion, protectorate, tributary, personal union, chartered
  company) keep their own monetary
  arrangement and may sign a 5a `currency_peg` with the overlord like anyone else. Asymmetry
  comes from the autonomy ladder that already exists, not from a new rule.
- **Subject:** the overlord's credibility, no dial, **`country_minting_mult = -0.5`**.
  **Overlord:** a flat **`country_minting_add`** equal to half the subject's minting, summed
  over its boards and re-applied yearly — *not* a `country_minting_mult`, which would scale
  the overlord's own base and transfer nothing. Be honest about the size: vanilla's base
  minting is a flat 500 and the real money is gold-mine PMs (125–1000 a level; the mod's late
  PMs reach 8250), so for a colony without gold both sides are rounding errors. This is a
  **gold-colony lever** — the Rand, Victoria — which is where the history is anyway. Needs a
  read of the subject's minting (`modifier:country_minting_add` in its scope — §17 check 21);
  fallback, count gold-mine levels.
- **The subject's lever:** a wrong stance sustained — the §13 counter **as shipped**, which
  keys on the *displayed band* (§0.4 P8), here at its extremes: band 1 or 5 for six
  consecutive months — adds `country_liberty_desire_add` while it lasts. Never the true gap:
  a modifier appearing at an exact gap would print a bit of r\*. An overlord running
  its rate for home conditions pays in unrest at the periphery; raising the subject's
  autonomy ends the board through the ordinary compare, and the subject exits *without* the
  5b exit penalty (it never chose to join).
- **Deferred:** an overlord interaction *Grant monetary autonomy* (board ends, autonomy
  unchanged). Named, not designed.

### 15A.5 Dependencies

5a needs phase 3 (`te_peg_confidence`, the crisis event, hot money) and phase 4
(`te_fx_index`, the float formula that becomes the shadow). 5b needs 5a's spine and its
LOLR event. 5c needs only the spine — it could ship before 5b. `te_mon_dollarised` (§9.2)
could later be re-expressed as "anchored to the hegemon"; recorded, **not** proposed — it
works, and its era-base derivation is what makes it a no-counterparty option.

---

## 15B. Leverage, coercion and exploit hardening (phase 6, proposed)

> **Not scoped — no owner decisions yet.** This section records what a design review of the
> shipped 5a articles (§15A.2) found missing or gameable, and sketches directions, not
> answers. Unlike §15A's "everything else is (proposed)", nothing here should be read as a
> committed shape — an implementer picking this up should treat the three subsections below
> as a punch list of open questions, weigh the tradeoffs noted inline, and is expected to
> bring their own ideas rather than just pick from these.
>
> **Planned and built 2026-09-21** — this punch list was turned into a staged plan, with every
> choice that is the owner's tagged for a ruling, in
> [§15C](#15c-phase-6-plan--leverage-coercion-and-exploit-hardening-built-2026-09-21), the owner's rulings on every one were taken the same
> day (§15C.5), and all thirteen shipped the same day. **What was actually built, and where it
> departs from the plan, is [§0.10](#010-phase-6-as-shipped--rulings-deviations-and-open-checks)** — read that first; the
> subsections below are the review that motivated the work, kept as written.

The review that motivated this section walked the shipped 110–112 treaty articles and their
effects/script-value chain end to end (not just the treaty-file comments) and found three
gaps, each below. All three read as gaps in the *same* place: 5a models voluntary,
symmetric-mechanic dependency (§15A "asymmetry... never from special-casing") and stops
there — no leverage accrues from it, no one can impose it, and the AI's caution about it is
evaluated once, at signing, and never revisited.

### 15B.1 Leverage and orbit-building

None of the three articles write `country_treaty_leverage_generation_add`. Several other
directed articles in the mod do — `common/treaty_articles/extra_treaty_articles.txt` grants
150–5000 leverage across a legal-jurisdiction article, a maritime-dominance article, and one
whose own comment names "the client's growing dependence" as the point. The three banking
articles model exactly that shape of dependency (a pegger living in the anchor's monetary
orbit; a ward whose finances answer to its guarantor) and generate none of vanilla's normal
currency for turning dependency into influence.

Directions to consider — not a shortlist to choose from, a starting point:

- A flat per-article `country_treaty_leverage_generation_add`, sized against the comparable
  articles above rather than against the 5000 outlier (tied to a much heavier commitment).
- Or leverage scaled the way the premium terms already are (§15A.1's GDP-ratio rule, or the
  reserve-currency share term, §15A.2) rather than flat per instance — flat-per-instance
  leverage would let the fan-out problem in §15B.3 (an anchor with unlimited peggers)
  snowball leverage the same way it already snowballs prestige.
- Whether leverage should reward *duration held* rather than mere existence — a peg or
  backstop that has survived several crises is a different kind of dependency than one
  signed last month, and nothing currently distinguishes them.
- Whether the weak side should earn anything symmetric. 5b already has a precedent
  (§15A.3: a holdout that refuses convergence pressure earns `country_leverage_resistance_add
  = 250` for ten years) for turning *enduring* a dependency, or *refusing* one, into
  something that isn't purely a cost. A ward that never calls its guarantee, or a pegger that
  rides out a crisis without breaking, might deserve the same kind of standing.
- Whether all three should generate the same amount. The three commit their stronger party to
  very different depths (a bare peg carries no obligation at all; a guarantee is the deepest),
  and vanilla's own leverage-granting pacts vary by what they actually commit — worth checking
  those before picking numbers.

### 15B.2 Hostile and coercive variants

All three articles are `friendly`-only. Every comparable *directed* article elsewhere in the
mod ships a `hostile` + `can_be_enforced` counterpart (Free Port Concession, Minority
Protection in `extra_treaty_articles.txt`) precisely because a directed article is normally
something a stronger power can impose on an unwilling counterparty, not just offer to a
willing one. The banking trio currently models only the Bretton-Woods, voluntary-cooperation
half of monetary history and none of the gunboat-diplomacy half — despite the AI-scoring
already treating the underlying dependency as something one side finds extractive.

The three don't carry the coercive framing equally well — **this is itself something the
implementer should weigh, not assume**:

- **`currency_peg`, imposed**: the best-attested historically (an occupying or dominant power
  forcing a currency board or peg on a weaker one — Panama's dollarization, interwar
  currency boards imposed as loan or reparations conditions). Note phase 5c already models
  the *subject* version of this (currency boards on `autonomy_level = 1` subjects,
  §15A.4) — an imposed peg would be the equivalent for a country that is *not* a subject.
- **`swap_line`, imposed**: the weakest fit. A swap line commits the *strong* side's own
  treasury (§15A.2, §0.8 ruling G6 — it's a real transfer, not flavour); forcing a country to
  lend against its will doesn't hold together the way forcing a peg does. A coercive version
  would have to coerce something else entirely (favorable currency-purchase or reserve terms
  extracted *from* the weaker side), which starts to look like a different article, not a
  hostile flag on this one. Worth asking whether this one should get a coercive variant at
  all, versus leaving the coercive angle to the other two.
- **`lender_of_last_resort`, imposed**: apt as *debt receivership* (the Dominican Republic
  1905, Egypt's Anglo-French debt commission, Venezuela 1902–03) — historically, the coercion
  isn't "force someone to guarantee you," it's forcing the weaker country to accept
  externally-supervised finances on one-sided terms. A hostile variant here probably isn't the
  friendly one's ward-benefit block with the sign flipped; it's a different relief/extraction
  shape.

Other things worth folding in if a hostile variant is built:

- The engine-constraints note at the top of `docs/vanilla/treaty_articles_reference.md`
  already documents `non_fulfillment` + `consequences = freeze` as the pattern for enforcing a
  directed article. None of the three current *friendly* articles use it either — a gap
  independent of the coercion question, and one the friendly versions might also want.
- A hostile variant's AI math can't just be the friendly version's mirrored: the friendly
  side's weak-party score is flatly eager (`+10`/`+20`/`+20`, no caution term at all, §15A.2)
  because the whole point there is that it's wanted. A coerced target should default to
  reluctant, the way any other `hostile` article's target does — that's a new score shape,
  not a re-signed one.
- Whether imposing one of these should route through a diplomatic play / war goal rather than
  ordinary treaty ratification, matching how vanilla usually gates imposing something on an
  unwilling target.

### 15B.3 AI logic and exploit hardening

These three are concrete, verified against the shipped effect and script-value files
(`te_monetary_arrangement_effects.txt`, `te_monetary_arrangement_script_values.txt`,
`events/te_monetary_arrangement_events.txt`) rather than inferred from the treaty-file
comments alone. Each is presented with what's actually in the code today and some directions;
none of the directions is a specification.

**Multi-provider swap-line stacking against a self-inflicted crisis.** `111_swap_line.txt`'s
`can_ratify` dedup only blocks the *same* provider granting a recipient a second line —
nothing caps how many *different* providers one recipient can hold at once, unlike
`lender_of_last_resort`'s explicit one-guarantor-per-ward check (112's can_ratify,
`te_lolr_already_guaranteed_tt`). `te_monetary_discover_arrangements` picks one provider a
month via `random_scope_article` (`te_monetary_arrangement_effects.txt:410`), so several
lines don't multiply a single month's draw — but they do mean the *real* treasury transfer
(`te_mon_swap_crisis_draw` = 0.1% of the recipient's own GDP a month, drawn provider →
recipient, `te_monetary_arrangement_effects.txt:596-603`) rotates across whichever provider
gets picked that month. `te_mon_in_external_crisis` (`te_monetary_triggers.txt:549`) is true
on `is_at_war = yes` **or** a banking panic/downturn — both are within a player's own control
to start and sustain — and nothing repays the draw. Directions: cap active swap-line providers
per recipient at one, mirroring LOLR; or keep multiple lines legal but make the draw
provider-*chosen* (with a cost/cooldown to switching) rather than randomly rotating; or
exclude a self-declared or below some scale/duration war from counting toward
`te_mon_in_external_crisis`; or put a lifetime or running cap on total drawn per relationship,
the way LOLR already caps calls per ward.

**Serial LOLR default farming.** Honouring costs the guarantor `5% of the WARD'S GDP`
(`te_mon_lolr_honour_cost`, ward scope) straight into the ward's treasury
(`te_lolr.1` option a, `events/te_monetary_arrangement_events.txt:41-51`), plus +25 relations
for the ward. The relief itself — `te_mon_lolr_relief_share = 0.5`, halving the ward's debt-load
premium — is what makes it *cheaper* for the ward to carry the debt that eventually defaults;
that's the moral-hazard loop the design intends to model (the AI's own GDP-scaled,
recipient-debt-penalized caution on the provider side says so), but nothing defends against a
player working it on purpose. `te_mon_lolr_default_cooldown_months = 60` is the only limiter,
and it resets rather than accumulating — nothing remembers how many times a given ward has
already been bailed out. The AI's `ai_chance` favors Honour over Renege roughly 5:1 before
modifiers (base 10 vs. 2, `te_lolr.1`), and same-power-bloc pushes further toward Honour;
only the guarantor's *own* debt level pushes back. Directions: a per-relationship repeat-call
counter that escalates the honour cost, decays AI willingness to Honour, or lengthens the
cooldown on each successive call; taper the relief itself against the ward's *own*
`scaled_debt` instead of a flat 50% regardless of how much it's already borrowing beyond what
the relief enabled; or give the AI a periodic post-signing re-evaluation (5b's convergence
pressure / holdout-question pattern is a precedent for exactly this) so a guarantor isn't
locked into whatever it agreed to at signing once the ward's debt has since spiraled.

**Uncapped pegger fan-out on the anchor side.** `te_mon_can_peg_to` gates who is *allowed* to
be an anchor (must hold a dial, be a major power+ or the pegger's own market owner) but caps
nothing about how many *different* countries can peg to the same anchor at once. The anchor
pays no maintenance (`maintenance_paid_by = target_country` — the pegger pays), takes on no
obligation, and gets `target_modifier = { country_prestige_mult = 0.02 }` per article in
force (§15A.2). Only the structural-premium half of the reserve-currency benefit is capped and
GDP-share-scaled (`te_mon_reserve_currency_cut`, capped at 0.5pp, §15A.1 script values); the
prestige half is a separate flat modifier that isn't routed through that same capped term, so
it plausibly scales with pegger *headcount* rather than with the GDP share the cap already
tracks (worth confirming in-game how the engine stacks repeated same-name modifiers from
several in-force treaty articles, before assuming this one). Directions: fold the anchor's
prestige benefit into the same capped, GDP-scaled reserve-currency calculation the structural
premium already uses, so there's one "being a reserve currency is prestigious" term instead
of an uncapped one that multiplies by count; or cap the pegger *count* directly, the way LOLR
caps guarantors per ward — though a headcount cap cuts against how reserve currencies actually
work (many real countries do peg to one anchor simultaneously), so it's the blunter of the two
options.

**The general pattern underneath all three.** Every article's AI score gives the dependent
side a flat, generous, uncaveated bonus (`+10`/`+20`/`+20`) with no matching caution term,
while the caution the design *does* have (GDP-scaled cost, recipient-debt penalties) lives
only on the strong side, and — per the LOLR case above — only ever runs once, at signing.
Before patching the three exploits individually, it's worth deciding whether that's the
intended shape (the strong side's caution is meant to be the *only* check, and the weak side's
eagerness is fine to leave unconditional) or whether some of it should also gate the weak side,
and whether a post-ratification re-evaluation belongs as a pattern shared by all three articles
rather than three separate ad-hoc fixes.

## 15C. Phase 6 plan — leverage, coercion and exploit hardening (built 2026-09-21)

> **Planned and built 2026-09-21.** §15B recorded what a review of the shipped 5a articles
> found. This section turned that punch list into a staged plan — files, variables, constants,
> AI terms, checks — with every choice that is the owner's tagged **H / L / C** and collected
> in §15C.5 for a ruling before code was written. Where the plan recommends, it says so and
> says what it rejected. Every number is still **(proposed)** until the harness has been run,
> like §0.8's G16.
>
> **It is now the plan, not the record.** All three sub-phases shipped on 2026-09-21, in one
> change rather than the four PRs §15C.5's "Sequencing" line proposed;
> [§0.10](#010-phase-6-as-shipped--rulings-deviations-and-open-checks) carries what was built,
> the deviations from this text, and what is still unverified. Where the two disagree, §0.10 is
> the shipped behaviour.
>
> **Owner rulings taken 2026-09-21 on all thirteen** (the table in §15C.5). Three depart from
> the recommendation — **H5** (prestige stays as shipped), **H6** (the engine's own AI withdrawal
> first; script only as a fallback) and **C4** (pretext: in default only) — and the sub-sections
> below carry the ruled shape, with the unadopted draft kept on record where it is worth having.

**Three sub-phases, each cuttable, in this order:**

| Sub-phase | What | Why this order |
|---|---|---|
| **6a — hardening** | close two of the three verified exploits (§15B.3 — the third, the pegger fan-out, is accepted as shipped by ruling H5), let the AI's post-signing withdrawal see the weak side's record, and add the `non_fulfillment` every directed article should have had | fixes shipped code; the smallest change; 6c's receivership reuses 6a's call counter and relief plumbing |
| **6b — leverage** | one modifier line per article | additive and independent; tiny |
| **6c — coercion** | two new hostile articles — an imposed peg and a debt receivership. **No hostile swap line** | the largest: new files, war goals, new AI shapes; needs 6a |

6b and 6c are independent of each other. All three sit under `te_mon_full_system` like the
rest of phase 5 (§0.9) and change nothing under the simplified rule.

### 15C.1 Phase 6a — exploit hardening

#### The swap line becomes a loan (§15B.3 "multi-provider stacking")

Three changes, in order of how much each does:

1. **The draw is repaid.** A recipient-side balance `te_mon_swap_drawn` (money, ≥ 0, seeded
   0, never removed) accumulates every crisis-month draw. **Out of a crisis with a balance
   outstanding, the same 0.1% of recipient GDP a month flows back, recipient → provider,**
   until the balance is 0 (`te_mon_swap_repay` = min(balance, `te_mon_swap_crisis_draw`)).
   No interest **(proposed)** — the recipient's own rate paid is already the price of its
   crisis. **The line has a limit:** the draw stops at `te_mon_swap_line_limit` = **2% of
   recipient GDP outstanding** (twenty months of draw), and the dashboard's *Backstops* row
   shows *drawn / limit*. A self-inflicted crisis then buys an interest-free loan of at most
   2% of GDP that comes straight back out — nothing to farm. Both flows live in step 9b's
   existing draw block (`te_monetary_apply_arrangement_modifiers`), which already does the
   cross-country `add_treasury` the right way round (G6).
2. **The line is called when it ends.** When the discovery sees `te_mon_swap_recipient` go
   1 → 0 with a balance outstanding — withdrawal by either side, a break, the provider losing
   its bank — the balance is settled **in one lump from the recipient's treasury** to
   `var:te_mon_swap_provider` (the scope variable still names the old provider: it is never
   removed, and the discovery reads it before it re-derives the role). Going into debt to
   settle is the honest outcome. No stain modifier — the settlement is the cost.
3. **One provider per recipient (H1).** `111_swap_line.txt`'s `can_ratify` gains the
   target-side check `112_lender_of_last_resort.txt` already has
   (`te_lolr_already_guaranteed_tt` → a `te_swap_already_provided_tt` twin). This makes
   `te_mon_swap_provider`'s "(first) provider" the only provider, so the balance in (1) is
   unambiguous and the `random_scope_article` pick in the discovery stops rotating.
   *Rejected:* keeping several lines and letting the recipient choose which to draw — it
   needs a picker UI and a per-provider balance the variable model cannot hold.

**War leaves the draw trigger (H2).** A new `te_mon_in_financial_crisis` =
`te_mon_in_external_crisis` without its `is_at_war` leg (panic / downturn, peg confidence
≤ 40, inflation band ≥ 6). **Only the draw reads it**; capital-controls forgiveness and the
AI's controls rule keep the wider definition — a war excuses controls, but a swap line is a
central bank's liquidity instrument, not war finance, and `is_at_war` is the one leg the
recipient can switch on at will. (Precedent for one consumer re-reading a narrower trigger:
G15's `te_mon_capital_controls_in_force`.)

**AI.** The provider's `inherent_accept_score` gains `te_ai_backstop_drawn`: a recipient
still owing *anyone* (`scope:target_country.var:te_mon_swap_drawn > 0`) is a credit already
extended, **−20 (proposed)**.

#### The guarantee remembers (§15B.3 "serial LOLR default farming")

**A ward's call counter, and everything reads it (H3).** `te_mon_lolr_calls` (0–5, ward
scope, seeded 0, never removed) is incremented by `te_monetary_on_country_default` when it
fires `te_lolr.1` — honoured or reneged alike. The counter is a fact about the *ward*, not
the guarantor, so it **survives a change of guarantor** (a ward cannot launder its record by
switching backers), and it forgets one call every ten years without a new one
(`te_mon_lolr_call_forget` = 120 months, re-armed on each call; at 0 with calls > 0, calls
− 1 and the clock re-arms — decremented in step 1c's clock section beside
`te_mon_lolr_default_cooldown`). Four sites read it, each with a **(proposed)** schedule:

| Site | Today | With `n` prior calls |
|---|---|---|
| honour cost (`te_mon_lolr_honour_cost`) | 5% of ward GDP | 5% × (1 + 0.5n), cap 15% |
| relief share (`te_mon_lolr_relief_share`) | 0.5, flat | 0.5 / 0.35 / 0.2 / **0** at n = 0 / 1 / 2 / 3+ — the moral-hazard loop closes on the third default |
| `te_lolr.1` AI odds (Honour base 10 : Renege base 2) | fixed | Honour 10 − 3n : Renege 2 + 2n — 10:2 → 7:4 → 4:6 → 1:8 |
| the ward's cooldown (`te_mon_lolr_default_cooldown_months`) | 60, reset each time | 60 × (1 + n): 5 → 10 → 15 years |

*Rejected:* tapering the relief against the ward's own `scaled_debt`. The relief is already a
share of the debt-load premium, so it already scales with debt, and a guarantee that shrinks
as the ward needs it is not a guarantee. The record, not the debt, is what a serial defaulter
has and an unlucky one hasn't.

**The signing score reads the record too (H4).** Both backstop articles' provider score gains
`te_ai_backstop_repeat_defaulter` = **−20 × `scope:target_country.var:te_mon_lolr_calls`
(proposed)**. `te_lolr.1`'s option tooltips gain a *this is its Nth call* line
(`te_lolr_calls_tt`).

#### Prestige stays as shipped (§15B.3 "uncapped pegger fan-out" — H5, owner ruling)

**Owner ruling 2026-09-21: leave the three articles' prestige lines as they are** — the anchor's
`target_modifier = { country_prestige_mult = 0.02 }` per pegger, the providers' 0.01 / 0.02 per
line or guarantee. The plan had proposed one managed, capped term in their place
(`te_mon_arrangement_prestige`, points = the reserve-currency cut × 10 plus provider cost × 2, so
+5% at the reserve cap and prestige only for what is actually carried); it is **not adopted**,
and no static modifier, variable or step-9b work for it is in 6a. Two consequences:

- the fan-out §15B.3 describes stays open **by decision**, so §20 risk 13's third item is
  accepted rather than mitigated;
- the engine question the managed term would have bypassed is **live** — how repeated same-name
  `target_modifier`s from several in-force articles stack on one country — and is now **§17
  check 24** / P6-7, to be read off a debug anchor with two and then three peggers.

The managed term stays on record here as the fix to reach for if that read, or an observer run,
shows an anchor's prestige running away with headcount. The two hostile articles (6c) carry
**no prestige line** of their own: a coerced peg is not a vote of confidence, and a receiver's
reward is leverage.

#### AI providers re-evaluate what they extend (§15B.3 "the general pattern" — H6)

**Ruling on the pattern: the caution stays on the strong side, but it now reads the weak
side's record and runs more than once.** The weak side's flat eagerness at signing
(+10 / +20 / +20) stands — a backstop *is* wanted, and 5b's holdout already answers what to
do when it isn't. What changes is that the strong side's `inherent_accept_score` is fed the
ward's calls and the recipient's drawn balance (H3, H4) — and **the owner's ruling (H6) is to
lean on the engine's own AI withdrawal first, and write nothing of our own unless it is not
there.**

What is known offline: the article `ai` block uses five keys across this repo's articles
(`treaty_categories`, `article_ai_usage`, `evaluation_chance`, `inherent_accept_score`,
`quantity_input_value`) and no withdrawal-specific one; the engine has a treaty-scope
`withdraw` effect, an `on_country_withdrawn_from_treaty` on-action, a binding period after which
either party may withdraw freely (`vanilla_diplomacy_reference.md` § treaties), and a
treaty-scope trigger **`is_equal_exchange_for = <country>`** — the engine's own acceptance
evaluation of an *existing* treaty, exposed to script. Whether the vanilla AI *acts* on that
evaluation for in-force treaties — withdrawing on its own once the score has turned against it
after binding — is **§17 check 22**, the first thing 6a's second PR settles in-game:

- **If it does** (the expected case): the H3 / H4 terms in `inherent_accept_score` are the whole
  implementation. A guarantor whose ward has been bailed out twice, or a provider whose
  recipient is still drawn, sees its score go negative and the engine's AI withdraws when the
  binding period allows. Nothing yearly is written.
- **If it does not**: the fallback is a yearly walk in `te_monetary_arrangement_yearly_on_action`
  for `is_ai = yes` providers with `te_mon_arr_provider_pts > 0`, which tests each treaty ROOT
  provides with **`NOT = { is_equal_exchange_for = root }`** — the engine's own evaluation, not a
  hand-restated score — and issues `withdraw = { country = root }`, **only when every article in
  the treaty is one of the monetary three** (G14: `withdraw` leaves the whole treaty; an AI must
  not drop a trade treaty because a swap line went sour). A mixed treaty is left standing and the
  AI eats the cost, the price of bundling. Precedent for an AI acting on a post-signing score
  from the pulse: the adopter's exit at 30 points of overvaluation
  (`te_mon_union_ai_exit_overvaluation`, G16). Only if `is_equal_exchange_for` turns out not to
  reflect the article scores of an in-force treaty does the last resort apply — a restated
  `te_mon_ai_keep_backstop_score` (the provider-side terms, the base removed, a +10 inertia term
  so a marginal line is not signed and dropped every other year).

Either way: **never for a player provider**, who has the dashboard row and the treaty UI; and
5b's leader is **not** covered — its backstop is a principle, not a treaty, and the pressure
toggle already has its own AI (G16).

#### `non_fulfillment` for the friendly three (H7)

All three articles gain `extend_influence`'s block (`extra_treaty_articles.txt`):
`consequences = withdraw` when the two are at war with each other or one has expelled the
other's diplomats, tested `weekly`. **`withdraw`, not `freeze`**, deliberately: §17 check 15 /
P5-2 (does a frozen treaty still iterate under `any_scope_treaty`?) is unanswered, and a peg
between belligerents should end, not pause. Withdrawal runs the ordinary hooks, so the
anchored state lapses — and, under the swap-line change above, the line is called.

#### Files, variables, constants (6a)

| Touch | Where |
|---|---|
| variables (seeded in `te_monetary_init_arrangement_variables`; contract comment in the values file header) | `te_mon_swap_drawn`, `te_mon_lolr_calls`, `te_mon_lolr_call_forget` |
| script values | `te_mon_swap_line_limit`, `te_mon_swap_repay`, `te_mon_lolr_honour_cost` (× calls), `te_mon_lolr_relief_share` (by calls), `te_mon_lolr_default_cooldown_months` (× calls); `te_mon_ai_keep_backstop_score` only as H6's last resort — `te_monetary_arrangement_script_values.txt` |
| triggers | `te_mon_in_financial_crisis` beside `te_mon_in_external_crisis` in `te_monetary_triggers.txt` |
| effects | step 9b's draw block (repay, limit); the discovery (settle on role end); step 1c's clocks (`te_mon_lolr_call_forget`); the yearly walk **only as H6's fallback** — `te_monetary_arrangement_effects.txt` |
| on-actions | `te_monetary_on_country_default` increments `te_mon_lolr_calls`; `te_monetary_arrangement_yearly_on_action` calls the H6 fallback, if one is written — `te_monetary_on_actions.txt` |
| event | `te_lolr.1`: `ai_chance` by calls, `te_lolr_calls_tt` — `te_monetary_arrangement_events.txt` |
| articles | 110 / 111 / 112: `non_fulfillment` in, 111's one-provider `can_ratify`, the two new AI `desc` lines (`te_ai_backstop_drawn`, `te_ai_backstop_repeat_defaulter`); prestige lines **unchanged** (H5) |
| GUI | the *Backstops* row gains a *drawn / limit* line |
| loc | the two `desc` keys and the tooltip keys — `te_miscellaneous_l_english.yml`, `te_events_l_english.yml` |
| harness | `te_debug_monetary.10` (or a `.11` if `.10`'s six options are enough already): pin a debug swap line the way `.10`'s option a pins an anchor; force `te_mon_in_financial_crisis` for a month; set `te_mon_lolr_calls` |
| docs | `mod_systems.md` § Monetary Policy (phase 5) → a phase-6 paragraph; `treaty_articles_reference.md`'s monetary table; a §0.10 here; §21 rows |

**Audits.** The new variables are clocks or balances and are never removed
(`modifier_multiplier_var_audit`); every new AI line carries `desc =`; every new tooltip key
has loc (`loc_coverage_audit`). Expected reload: no findings.

### 15C.2 Phase 6b — leverage

**One flat `country_treaty_leverage_generation_add` per article (L1).**

> **Correction, 2026-09-21.** The ruling below said "on the strong side's modifier block", and
> phase 6 shipped it that way. That is backwards: the engine generates this leverage **against**
> the country whose modifier block carries it, not by it. Vanilla is unambiguous —
> `guarantee_independence` puts the line on the *guaranteed* party (`target_modifier`, source
> being the higher-ranked guarantor), and `foreign_investment_rights` / `trade_privilege` /
> `host_power_bloc_embassy` put it on the party that *grants* the concession (`source_modifier`).
> The mod's own `development_assistance` already had it right, on the client's `target_modifier`.
> In-game the shipped placement let the pegger accumulate leverage on its anchor. Corrected in all
> five articles: the line now sits on `source_modifier` for `currency_peg`, `imposed_currency_peg`
> and `debt_receivership` (pegger / coerced pegger / debtor are the sources) and on
> `target_modifier` for `swap_line` and `lender_of_last_resort` (recipient / ward are the targets).
> The values below are unchanged. The three legacy articles — `request_influence`,
> `extend_influence`, `crisis_resolution` — were audited at the same time and are correct as
> written.

The magnitudes, sized against the comparable articles:

| Article | Leverage | Sized against (`extra_treaty_articles.txt`) |
|---|---|---|
| `currency_peg` | **200** | `development_assistance` (200, "the client's growing dependence"): a pegger lives in the anchor's monetary orbit |
| `swap_line` | **150** | `joint_military_exercises` (150): a standing line is the lightest dependence of the three |
| `lender_of_last_resort` | **300** | `intelligence_sharing_pact` (300): a ward's finances answer to its guarantor |

All **(proposed)**. Two engine facts settle §15B.1's worries. The modifier generates leverage
**only when the dominant country leads a power bloc** (its own definition,
`docs/engine/vic3_modifier_type_definitions_reference.md`), so for anyone else it is inert,
as vanilla's own pacts are. And leverage is generated **per pair**, out of the *target's*
fixed pool (`vanilla_diplomacy_reference.md` § leverage): an anchor with ten peggers has
leverage on ten countries, which is orbit-building, not a stack on one. So flat-per-article
does **not** snowball the way the prestige did, and no scaling is needed. *Rejected:*
leverage by duration held — no per-article age is readable from script that anyone has
verified, and vanilla's pacts are flat; and scaling by the GDP-ratio term — leverage is
about the *weak* side's dependence, which the ratio measures upside down.

**Nothing symmetric for the weak side (L2 — recommend defer).** 5b's holdout earns
resistance for *refusing* an orbit; a ward that never calls its guarantee, or a pegger that
rides out a crisis, chose the orbit and stayed. Rewarding that with leverage resistance would
pay a country for the dependency it is in. Named, not designed — revisit only if observer
runs show AI minors never leaving an anchor.

Files: one line in each of 110 / 111 / 112; the engine-built effects text picks the modifier
up; `treaty_articles_reference.md`'s table. Nothing else.

### 15C.3 Phase 6c — coercive variants

**The framing questions in §15B.2, answered.** The engine already routes imposition through
a diplomatic play: an article with `can_be_enforced` and a `wargoal` block is exactly what a
play can demand (every hostile article in `10x_*.txt` does this), so no new play or war-goal
type is needed. A hostile variant is a **separate article type** — `friendly` / `hostile`
are flags of the type, and the mod's precedent (Free Port, Minority Protection) is one file
per variant — not a flag on the shipped one. And the mod's direction convention for hostile
directed articles is **source = the party that concedes, target = the imposer**
(`103_free_port_concession.txt`: "Source (losing tariff sovereignty) is reluctant"), which
is the friendly peg's direction already (pegger → anchor).

#### `imposed_currency_peg` — `113_imposed_currency_peg.txt` (C1)

Source = the pegger (concedes), target = the anchor (imposes). `hostile`, `can_be_enforced`,
`can_be_renegotiated`; `article_ai_usage = { request }`; cost 100; `maintenance_paid_by =
target_country` (the imposer wants it, the imposer pays — the Free Port rule); the peg's
tech gate (`international_exchange_standards`); `visible` under `te_mon_full_system`;
**mutually exclusive with `currency_peg`, declared in both files**.

- **The pegger is kind 1 exactly as under the friendly peg** — one anchored state (§15A's
  owner decision) — so the discovery, `te_mon_has_peg_article`,
  `te_mon_has_valid_peg_article`, 110's *already pegged* `can_ratify` and
  `te_mon_effect_anchor_peg_break` each gain `OR = { has_type = currency_peg has_type =
  imposed_currency_peg }`. What differs is the terms, all **(proposed)**: spread **1.0**,
  not 0.5 (`te_mon_anchor_spread_peg_imposed` — a penalty rate, the currency-board-at-gunpoint
  shape); **no** `te_mon_peg_standing_cut` — the −0.5pp structural cut is the market's reward
  for a *chosen* discipline; `source_modifier` `country_legitimacy_base_add = -10` (Minority
  Protection's "the government looks weak for ceding sovereignty" line); 6b's leverage at
  **400** on the imposer; **no prestige line** (H5 — a coerced peg is not a vote of confidence).
- **`te_peg.2`'s *Break the peg* is unavailable to an imposed pegger** (a `trigger =` on the
  option, `te_peg_events.txt`): Defend and Re-peg lower remain. Its way out is the treaty UI,
  where withdrawal from an enforced article is what the imposer's war goal exists to answer.
- **Pretext (`possible`, C4 — owner ruling: in default only)**, so the AI world does not fill
  with imposed pegs: the imposer holds a dial and is a major power or better; the target is
  **`in_default = yes`**. The wider draft (inflation ≥ 10, or living in the imposer's market)
  was **rejected** as too loose: a currency in trouble, or in the imposer's economic space, is
  not by itself grounds; an insolvent government is.
- **AI**, the Free Port shape: pegger base **−20** (its government is already insolvent, so a
  rescue is a rescue — the pretext makes the draft's "+20 if in default" a constant, folded
  in), +10 in the hyperinflation band, −20 hostile attitude to the imposer; imposer +15
  `domineering`, +10 the target in its market, +10 great power, −20 friendly attitude
  (`population_transfer`'s rule: don't impose on friends). `evaluation_chance` 0.01, +0.05
  when `domineering` (the pretext is already the gate).
- **`wargoal`**: `contestion_type = control_target_country_capital`
  (`105_enforce_privatization.txt`), `execution_priority = 60`, the Free Port maneuvers /
  infamy template with `INFAMY_BASE_VALUE` **8** — more than a port, less than a disarmament.
- **Not phase 5c's board.** A subject with `autonomy_level = 1` is already kind 3 by rule
  (§15A.4); an imposed peg is the same instrument for a country that is *not* a subject, and
  the precedence rule (highest kind wins) means subjugating an imposed pegger simply promotes
  it to a board.

#### `debt_receivership` — `114_debt_receivership.txt` (C2)

The coercive counterpart to the guarantee is not a guarantee at gunpoint; it is **the weaker
country accepting externally supervised finances** (§15B.2: Egypt's Caisse de la Dette 1876,
the Ottoman Public Debt Administration 1881, the Dominican customs receivership 1905).
Source = the debtor (concedes), target = the receiver (imposes). `hostile`,
`can_be_enforced`, `can_be_renegotiated`; `article_ai_usage = { request }`; cost 150; the
imposer pays maintenance; tech **`international_exchange_standards` (proposed)** — the
history is era 3–4, and the friendly guarantee's `intergovernmental_organizations` is a
Bretton Woods idea that would put the receivership two eras after the thing it models;
**mutually exclusive with `lender_of_last_resort`, declared in both files** (two names behind
one debt are not two rescues).

- **Pretext (`possible`, C4 — owner ruling: in default only)**: the debtor is **`in_default =
  yes`** (the draft's `scaled_debt ≥ 0.75` alternative was **rejected**); the receiver passes
  `te_mon_can_backstop` (a national bank, outranks or out-GDPs) with the roles swapped.
- **The debtor:** the guarantee's relief (`te_mon_lolr_relief`, through a new role flag
  `te_mon_receivership = 1` read by `te_mon_arr_recipient_value`) — creditors *are*
  reassured by a receiver, which is why the instrument existed — but it pays for it monthly:
  `te_mon_receivership_take` = **0.1% of debtor GDP a month, debtor → receiver** ("the
  customs receipts"), reusing the swap draw's step-9b plumbing in the other direction; plus
  `source_modifier` `country_legitimacy_base_add = -10`. The debtor's default under a
  receivership pays it nothing: the receiver is a creditor, not a guarantor, so **no
  `te_lolr.1`** (`te_monetary_on_country_default` tests the guarantee, not the receivership).
- **The receiver:** the take; 6b's leverage at **500** — the heaviest, because §15B.1's
  "client's growing dependence" is the literal thing here; and a receivership cost line in
  `te_mon_arr_provider_pts` at the GDP-ratio rule (it does carry a share of the relief, as a
  guarantor would). **No prestige line** (H5 — the receiver's reward is leverage).
- **The exit ramp:** `non_fulfillment = { consequences = withdraw }` once the debtor has had
  `scaled_debt < 0.25` and no default for twelve consecutive months (`monthly`, a small
  counter) — the receivership ends when the debt is worked down (the Dominican 1941 shape),
  so it is a sentence, not a permanent tribute. `requirement_to_maintain`: the receiver
  solvent (112's `te_lolr_guarantor_solvent_tt`).
- **AI**: debtor base **−10** (the pretext means it is already insolvent and takes the receiver
  over the creditors' gunboats — the draft's −40 + 30-if-in-default, folded), −20 hostile
  attitude; receiver +20 the debtor in its market,
  +10 great power, +15 `domineering`, −20 friendly attitude. `evaluation_chance` 0.01, +0.08
  for a `domineering` receiver with a debtor in its market.
- **`wargoal`**: `control_target_country_capital`, `execution_priority = 70`, infamy base
  **10**.

#### No hostile swap line (C3 — recommend)

§15B.2's own analysis holds: a swap line commits the *strong* side's treasury, forcing a
country to lend is not a thing history did, and "reserve terms extracted from the weaker
side" is what the receivership's take already is. The swap line stays `friendly`-only.

#### Files, variables (6c)

New: `113_imposed_currency_peg.txt`, `114_debt_receivership.txt` (their headers cite this
section); `te_mon_receivership` (0 / 1) and `te_mon_receiver` (scope, the `te_mon_anchor`
contract) in the variable contract, discovered beside the guarantee roles;
`te_mon_anchor_spread_peg_imposed`, `te_mon_receivership_take`, the twelve-month exit
counter; `te_mon_is_imposed_pegger` (the peg article walk with the type); the `OR = {
has_type … }` edits listed under C1; the `te_peg.2` option trigger; the AI `desc` keys and
the two articles' name / desc / effects / short-desc keys (the engine-built `*_effects_desc`
keys land in `te_unused_l_english.yml` like every article's — §0.8 known roughness);
`treaty_articles_reference.md` gains two rows; `mod_systems.md`.

### 15C.4 Checks and the harness (P6-1…13)

§17 gains three checks. **Check 22 (H6)**: does the vanilla AI withdraw on its own from an
in-force treaty whose article `inherent_accept_score` has turned negative for it, once the
binding period allows? Read on a debug guarantor with the ward's `te_mon_lolr_calls` set to
2. If not, the fallback walk has its own sub-check: a `withdraw = { country = root }` issued
from a scripted effect on the yearly pulse fires `on_withdrawal` with
`scope:withdrawing_country` set, as it does from an event option (P5-9). **Check 23**:
`control_target_country_capital` on a hostile monetary article resolves in the play UI
(in-mod precedent, low risk). **Check 24 (H5)**: how repeated same-name `target_modifier`s
from several in-force articles stack on one country — read the anchor's prestige with two,
then three, debug peggers. Check 14's cousin, live again because the shipped prestige lines
stay.

Checklist, run with `te_debug_monetary.10` and the new options, before any sub-phase is
called done:

- **P6-1.** A debug swap line drawn for six crisis-months shows *drawn* = 0.6% of GDP, stops
  at 2%, and repays at 0.1% a month once `te_mon_in_financial_crisis` clears; the provider's
  treasury shows both legs.
- **P6-2.** Ending the line with a balance outstanding settles it in one lump from the
  recipient — including into debt.
- **P6-3.** A second provider cannot ratify a swap line for a recipient that has one;
  `te_swap_already_provided_tt` renders from both sides.
- **P6-4.** A recipient at war but in no financial crisis draws nothing; one in a panic draws.
- **P6-5.** Three defaults in a row: honour cost 5% → 7.5% → 10%, relief 0.5 → 0.35 → 0.2 →
  0, cooldown 5 → 10 → 15 years, `te_lolr.1`'s AI odds shift as tabled; the counter survives
  a change of guarantor and forgets one call after ten quiet years.
- **P6-6.** A prospective guarantor's tooltip shows `te_ai_backstop_repeat_defaulter` on a
  ward with calls > 0, and `te_ai_backstop_drawn` on a recipient still owing.
- **P6-7.** (check 24) An anchor with two, then three, peggers shows +4% then +6% prestige if
  same-name article modifiers stack additively — or something else, which is the answer to
  write down. The fan-out is accepted as shipped (H5), so this row records; it does not fail.
- **P6-8.** (check 22) An AI guarantor whose ward's calls have driven its score negative
  withdraws on its own once the binding period allows. If the engine does not, the fallback
  walk withdraws within a year — from a monetary-only treaty, never from a bundled one. A
  player provider is never withdrawn for, either way.
- **P6-9.** War between the parties, or expelled diplomats, ends each of the three articles
  within a week; the pegger's kind reads 0 next month.
- **P6-10.** 6b: with the anchor a bloc leader, the pegger's leverage panel shows the treaty
  line at 200; with the anchor not a leader, nothing.
- **P6-11.** 6c: an imposed peg reads kind 1 with spread 1.0 and no standing cut; *Break* is
  absent from `te_peg.2`; withdrawal by the pegger gives the imposer the enforce play; a peg
  and an imposed peg cannot coexist.
- **P6-12.** 6c: a receivership shows the take on both sides and the relief on the debtor, no
  `te_lolr.1` on the debtor's default, and withdraws itself twelve months after
  `scaled_debt < 0.25`.
- **P6-13.** In a 50-year observer run, imposed pegs and receiverships are **rare** — a
  handful a campaign, only with a pretext — and the AI still signs the friendly three (P5-7
  still holds).

### 15C.5 Owner decisions — rulings taken 2026-09-21

| # | Decision | Recommended | Alternative | Cost to reverse | **Ruling (2026-09-21)** |
|---|---|---|---|---|---|
| **H1** | one swap-line provider per recipient | **yes** (LOLR's rule) | several lines, recipient-chosen draw | one `can_ratify` block | **Yes** — one provider |
| **H2** | war out of the draw trigger | **yes** | keep `is_at_war` (wartime lending is historical: 1914–18) | one trigger name in step 9b | **Yes** — financial crises only |
| **H3** | the call counter's four schedules | as tabled | any subset (the relief taper alone closes the loop) | constants | **All four**, as tabled |
| **H4** | the record in the signing score, −20 per call | **yes** | — | one `desc` line each | **Yes**, −20 per call |
| **H5** | one managed prestige term replacing all three flat lines | **yes** | fix the anchor side only; leave the providers' 0.01 / 0.02 | three modifier lines | **Leave prestige as shipped** — not adopted; check 24 records the stacking |
| **H6** | AI providers re-evaluate yearly and withdraw from monetary-only treaties | **yes** | at signing only (today) | delete one effect | **Use the engine's own AI withdrawal if it re-evaluates in-force treaties** (check 22); the scripted walk only as a fallback, on `is_equal_exchange_for` |
| **H7** | `non_fulfillment = withdraw` on war / expulsion | **yes** | `freeze` (needs check 15 answered first) | one block each | **Yes** — `withdraw` |
| **L1** | flat leverage 200 / 150 / 300 | **yes** | scaled, or none | one line each | **Yes** — 200 / 150 / 300 |
| **L2** | leverage resistance for the weak side | **defer** | 5b-style resistance for a never-called guarantee | — | **Defer** |
| **C1** | an imposed peg: spread 1.0, no standing cut, −10 legitimacy, 400 leverage | **yes** | no coercive variants at all (5a stays voluntary) | a file | **Yes**, as specified (no prestige line) |
| **C2** | a debt receivership at `international_exchange_standards`: 0.1% take, 500 leverage, self-ending | **yes** | a later tech; a tribute with no exit ramp | a file | **Yes**, at `international_exchange_standards` |
| **C3** | no hostile swap line | **yes** | — | — | **Yes** — no hostile swap line |
| **C4** | 6c's pretexts (`possible`) as written | as written | narrower (in default only), or none (any great power may demand) | trigger lines | **Narrower: in default only** |

**Sequencing.** 6a as two PRs (the swap line and the guarantee; then `non_fulfillment`, the
check-22 read and, only if it fails, the fallback walk), 6b as one, 6c as one per article —
each with a clean `mod_only` reload, the
P6 rows it can reach, and its §0.10 entry written at the time. Before 6a ships, §0.8's P5-5,
P5-7 and P5-9 should have been seen in a running game once: 6a changes the numbers those
rows check.


---

## 16. Implementation mapping

### 16.1 Interest plumbing — country scope

Countries without the JE or a national bank must still pay world rate + premium, and
JE-scope `multiplier =` cannot read country properties (`scripting_best_practices.md:400`).
So the rate lives in **country scope**, refreshed for every country.

**AS SHIPPED (revised 2026-09-19): ONE static modifier, not two.** The design below
described a pair — an offset cancelling vanilla's flat base, plus the rate itself. That
pair shipped and was then collapsed: vanilla's flat base is cancelled on the entity that
grants it, by `country_loan_interest_rate_add = -0.2` in the mod's `INJECT:base_values`
block, the same treatment the ranks and the finance techs get. `te_monetary_base_offset` is
deleted. The player sees one interest line instead of a +20% base with a −20% modifier
beside it.

```
INJECT:base_values = { … country_loan_interest_rate_add = -0.2 }    # cancels vanilla's flat 20%
te_monetary_rate_paid = { country_loan_interest_rate_add = 0.01 }   # multiplier = var:te_rate_paid_applied
```

**Where it lives (changed 2026-09-20):** on `je_banking_cycle` for a country that holds the
entry, on the country otherwise — the same HOME mechanism as the inflation bands. It was the
one deliberate exception to the JE-scope convention until the owner asked for it on the entry;
the reasoning, and what to revert if the budget's interest breakdown stops naming the line, is
in the `WHERE THE MODIFIERS LIVE` comment in `common/scripted_effects/te_monetary_effects.txt`.
Step 9 therefore goes through `te_mon_mod_strip` / `te_mon_mod_add_scaled`, and reads presence
with the `te_mon_mod_has` trigger — a bare country-scope `has_modifier` is silently false for
any country holding the entry.

**Consequence:** a country with no rate modifier now sums to **0%**, not vanilla's 20%. The
owner has confirmed in game that a non-positive total simply displays 0.0% with no ill
effect, so the old "Σ`_add` never sits at ≤ 0" invariant is retired. Skip the re-apply when
the change since last month is under 0.05. `REPLACE` the `country_loan_interest_rate_add`
**modifier type definition** to `decimals = 1` (precedent:
`common/modifier_type_definitions/mod_entity_modifier_types.txt:3486`). The flat-key INJECT
is §17 check 2, and the owner read it in game on 2026-09-20: it **sums** — see §0.3 item 1b.

- **Run the update from `on_game_started` as well as the monthly pulse.** The
  cancel-`INJECT`s apply on day one but the rate modifier would not exist until the first
  pulse; several tags start in debt, and they would borrow free for that month. **Also call
  it from the country-creation on-actions** — civil-war and released tags would otherwise
  borrow free until their first pulse, exactly when the player is looking at them.
- **BUT NOT DIRECTLY FROM EITHER (fixed 2026-09-19).** `add_modifier`'s `multiplier =` is
  resolved against **ROOT**. `on_game_started` has no root scope at all and the six
  country-creation hooks leave the **parent** in ROOT, so the first write applied every
  country's rate at a multiplier of 1.0 (and would have stamped a parent's rate onto a
  released tag). Both families dispatch a hidden country event, `te_monetary_internal.1`
  (`events/te_monetary_events.txt`), whose ROOT is the country it fires on; it runs the whole
  update, so each entry point still causes exactly one, non-doubled call.
  `on_monthly_pulse_country` and `on_country_formed` declare "Expected Scope: country" and
  call the effect directly. Step 9 carries a `te_rate_paid_rooted` marker — set only when
  `root ?= this` — so anything applied root-less is repaired on the next monthly pulse; it is
  the one monetary variable deliberately not initialised. Full write-up:
  `scripting_best_practices.md` § "`add_modifier { multiplier = var:X }` Resolves Against
  ROOT".
- **`-0.2` hardcodes vanilla's `base_values` rate.** When phase 1 ships, add a line to
  `docs/guides/vanilla_patch_runbook.md` so a vanilla change to
  `country_loan_interest_rate_add` in `00_code_static_modifiers.txt` gets caught — along
  with the six rank mults, laissez-faire and the five tech values the cancel-`INJECT`s mirror.

**No `REPLACE` of any vanilla database entity (ranks, laws, techs, static modifiers) —
cancel-`INJECT`s only.** Rejected alternatives:
`REPLACE:base_values` (must restate an engine-named block plus the mod's own 40-key
`INJECT:base_values`, re-diffed every patch; and any REPLACE silently drops every INJECT
into that entity); a back-solver over `modifier:country_loan_interest_rate_mult` (the
division blows up as 1 + Σmult → 0, which vanilla stacks can already reach).

**Do not gate the plumbing on `banking_system_enabled`.** The cancel-injects are file-level,
so with the rule off a passive pulse (constant reference rate + premium) must still run.
**That passive pulse is now exactly what the `banking_system_simplified` setting ships** — see
[§0.9](#09-the-banking_system_simplified-game-rule--2026-09-21). Everything above this line runs
under all three settings of the rule; everything gated on `te_mon_full_system` does not.

### 16.2 Single owner: the monthly country update

New on-action on `on_monthly_pulse_country` calling `te_monetary_monthly_update`. **No new
variable goes in `je_banking.txt`'s `immediate`** — that block resets unguarded
(`:119-133`) and the JE is `can_revolution_inherit`. Every variable initialises behind
`has_variable`, and **none is ever removed** (`modifier_multiplier_var_audit`).

Order: 0 init → 1 regime code → 2 target (mandate if delegated / AI / CBI / bank-without-JE,
else player's var; round + hysteresis; clamp to regime) → 3 drift → 4 no-dial = world +
expected + spread → 5 premium (structural, floored; then cyclical) → 6 *[P2]* basket →
core → headline → expected → 7 market yield → rate paid → 8 stance gap + displayed band →
9 re-apply interest modifiers → 10 *[P3]* gold flow / hot money / peg confidence.

Phases 4–5 insert, without reordering the above: **1c** *[P5]* anchor validity (monthly
check of the stored pair; discovery is event-driven with a yearly full scan — §15A.1), before
step 2 so the dial test sees it; **5b** *[P4]* FX (shock decay → `fx_target` → shadow →
index by regime → overvaluation → `te_fx_avg`), after the
premium it reads and before step 6 whose cost-push reads it; `te_mon_premium_fx` and the
phase-5 overvaluation premium are read in step 5 **from last month's index** (a one-month
lag, deliberately — it breaks the premium ↔ FX loop inside a single tick); **9b** *[P4/P5]*
re-apply `te_fx_weak` / `te_fx_strong`, `te_capital_controls_fatigue` and the two
arrangement modifiers.

| Variable | Range | Phase |
|---|---|---|
| `te_policy_rate_target` | regime range, integer | 1 |
| `te_policy_rate` | same, fractional | 1 |
| `te_mon_delegated` / `te_mon_mandate` | 0–1 / 1–3 | 1 |
| `te_premium_structural` / `te_premium_cyclical` | floor–30 / −10–40 | 1 |
| `te_rate_paid_pts` | 0.5–60 | 1 |
| `te_neutral_rate` / `te_neutral_error` | 1–6 / ±1.5 (hidden) | 1 |
| `te_mon_stance_gap` / `te_mon_stance_band` | −10–10 (hidden) / 1–5 (displayed) | 1 |
| `te_inflation_core` / `te_inflation` (headline) / `te_inflation_expected` | −10–100 | 2 |
| `te_basket_index` / `te_basket_avg` | −1–1 | 2 |
| `te_monetisation_level` | 0–3 | 2 |
| `te_gold_hot_money` | ≥ 0 | 3 |
| `te_peg_confidence` | 0–100 | 3 |
| `global_var:te_world_rate` | real rate | 3 |
| `global_var:te_world_inflation` | expected inflation, GP mean | 4 |
| `te_fx_index` / `te_fx_avg` / `te_fx_shock` | 50–150 / 50–150 / ±30 | 4 |
| `te_capital_controls_months` / `te_fx_devalued_months` | 0–60 / 0–36 | 4 |
| `te_fx_shadow` / `te_mon_overvaluation` / `te_mon_world_inflation_now` | 50–150 / 0–100 / pp | 4 |
| `te_mon_anchor` / `te_mon_anchor_kind` | scope / 0–3 | 5a |
| `te_mon_union_member` / `te_mon_union_last_asked` | 0–1 / date | 5b |

**Arithmetic with `change_variable`.** Drift: temp = target − actual; if temp > 0.34 add
0.3333, if < −0.34 subtract 0.3333, else set actual = target. Moving average: temp =
observation − average; multiply by α; add `var:tmp`. `change_variable`'s op slots accept a
literal, a `var:X` or a **script value name** — but not a bare trigger-dispatched read
such as `gdp` or `total_population` (`scripting_best_practices.md:1622-1624`), so anything
built from country triggers goes through a named script value or a cached variable first.
Inline block arithmetic inside `multiplier = { }` is the other trap (`:431`).

### 16.3 Stance into the JE pulse

No scaled modifier (§8 — it would print r\*). Inside `banking_cycle_advance_variables`,
next to the existing `modifier:` reads, add the stance directly:
`change_variable = { name = finance_cycle_momentum add = <script value: −0.125 × clamped gap> }`
and the same for `bubble_pressure` at −0.75. The gap is a country variable, so there is no
JE-scope multiplier, no `owner = { }` wrapper and no one-month lag. The investment-pool
effect is one of five banded JE-scope static modifiers (`banking_stance_band_*`), swapped
when `te_mon_stance_band` changes — decide from the variable just written, never from
`has_modifier` inside the same block (`scripting_best_practices.md:433-462`). Because the
country update and the JE pulse may run in either order (§17 check 7), the consumer must
tolerate a gap that is one month old.

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

> Phase 1 has shipped, so checks 1–4 and 6 are now part of the single consolidated list in
> [§0.3](#03-in-game-verification-checklist) — run that, not this. Check 6 was **bypassed**
> rather than answered (§0.1: the widget uses the vanilla-proven `GetPlayer.` form). Phase 2
> has shipped too, and with it checks **10** (`mg:` in an untraded market) and **12** (the
> deficit units) became live code: they are §0.4 checklist items **16** and **15**
> respectively, with the debug read-out that settles each. The remaining checks below still
> belong to phases 3–5.
>
> **Phase 5 has shipped** (§0.8): checks **15, 17, 18 and 21** are live code — §0.8 checklist
> items P5-2, P5-11, P5-1 and P5-12 — and checks **14 and 16 were bypassed** rather than
> answered (rulings G8 and G10: no monetary term lives in a treaty modifier block, and the
> union's tier is read through `has_principle`).
>
> **CHECKS 1–4 ARE ANSWERED (owner, in game, 2026-09-19 and 2026-09-20): `INJECT:` SUMS with
> vanilla's values** — nested `modifier = { }` blocks on ranks, technologies and laws, and a
> flat key inside a static modifier (`INJECT:base_values`) alike. Nothing below about
> last-wins came to pass; the fallbacks are kept only as the recipe for some future entity
> type that turns out to differ. Details in §0.3 items 1 / 1b and in
> `scripting_best_practices.md` § INJECT.

**Phase-1 coding gate.** Checks 1–4 need **no new code** — read tooltips on the current
build. They decide whether cancel-`INJECT`s sum with vanilla's values or overwrite them. If
INJECT is last-wins, `+0.5` on `great_power` would **double** a GP's rate instead of
zeroing its mult.

**These are worth running now, whenever monetary policy lands:** they also test a system
that is already live. `common/laws/sol_expectations_vanilla_injections.txt` (e.g.
`law_industry_banned`: `state_expected_sol_mult = 0.1` against vanilla's −0.1) has shipped
since April on the same unproven `INJECT` behaviour. If `INJECT` is last-wins, those laws
are wrong in play today.

1. A great power's budget-panel interest tooltip: does it still list rank −50% and
   laissez-faire −25%? If yes, separate `modifier = {}` blocks merge (the mod already
   INJECTs both).
2. The breakdown of `state_expected_sol_from_literacy`: the mod injects −5 against
   vanilla's +5 (`extra_modifiers.txt:17`). **Three outcomes: 0 ⇒ values sum; −5 ⇒ last
   wins; +5 ⇒ the inject is ignored.** Caveat: this is a *flat key inside a static
   modifier*, and `common/static_modifiers` is not on the 1.12 digest's INJECT-capable list
   even though `INJECT:base_values` demonstrably works — ranks, laws and techs merge a
   *nested* `modifier = { }` block, so do not let this result stand in for them.
3. Does expected SoL under `law_industry_banned` net to zero (same key summing across blocks)?
4. **A technology probe.** Five of the twelve cancel-`INJECT`s are on technologies, and
   `scripting_best_practices.md` § INJECT already warns that merge semantics vary by entity
   type; checks 1 and 3 only cover a rank and two laws. The mod already INJECTs
   `modifier = {}` into vanilla techs in `common/technology/technologies/modified.txt`
   (`intensive_agriculture`, `nationalism`, …): does vanilla's own modifier still show in
   the tech tooltip?

**Whatever the results, record them in `scripting_best_practices.md` § INJECT in the same
session** — it is the most reusable fact this work will produce.

Fallbacks if summing fails — techs: `REPLACE` the five in
`common/technology/technologies/te_monetary_tech_injections.txt`, restating each vanilla
`modifier = {}` block minus the interest line (§0.1 R3 chose the cancel-`INJECT` over
script compensation; compensating in `te_premium_structural` instead, touching no vanilla
entity, remains available). Note that the five vanilla techs carry
`country_minting_mult = 0.1` in the same `modifier = {}` block as the interest line, so a
last-wins cancel-`INJECT` would wipe their minting bonus too — which is the tell §0.3's
checklist item 1 reads; ranks / laissez-faire: `REPLACE` in
`common/country_ranks/extra_country_ranks.txt` — owed regardless in that case, because the
mod's existing GP/major INJECTs would already be wiping vanilla's blocks.

Later checks:

5. `modifier:country_loan_interest_rate_add` / `_mult` readable in a script value? (The mod
   already reads other `base_values` keys this way; this pair is unverified. Used only for a
   debug readout.)
6. `[JournalEntry.GetCountry.GetYearlyInterestRate|1%]` in widget loc — the `GetPlayer.`
   form is proven, the `Country.` form is not.
7. Relative order of global `on_monthly_pulse`, `on_monthly_pulse_country` and the JE's pulse.
8. Does `add_modifier` accept a **negative** multiplier? (Base-offset variant only. The
   stance channel no longer needs it — §8 applies the stance through the variable update and
   fixed-sign banded modifiers. `banking_cycle_update_fiscal_policy` already feeds a signed
   value into a multiplier, so this and check 12 can be settled by the same observation.)
9. Does the engine's per-loan interest bucket already scale with debt? (§7.6.)
10. `mg:<good>` reads in a market that never traded the good (§9.3).
11. A one-off `add_treasury` above the gold reserve limit — diminishing returns? (§12.2; the
    scripted `scaled_gold_reserves` cap is the stated fallback, not the engine.)
12. Is the existing fiscal-policy input live, and in what units?
    `financial_cycle_government_fiscal_policy_effect_size` reads `total_expenses` / `income`
    / `gdp` bare but is applied as a **JE-scope** multiplier (`banking_cycle_effects.txt`,
    `banking_cycle_update_fiscal_policy`), which `scripting_best_practices.md:400` says
    evaluates to `'none'`. No error appeared in the 2026-09-19 `debug.log`, so this is
    unconfirmed — check the modifier's value on the JE while running a known deficit. The
    same observation settles the **weekly-vs-annual units** question (§9.1): a 1%-of-GDP
    annual deficit should read 1.0, not ~0.02. Either way, **do not copy that shape**:
    §9.1's deficit term runs in country scope and caches to a variable.

Phases 4–5 (§15, §15A):

13. Do `state_export_advantage_mult` / `state_import_advantage_mult` on a **country-scope**
    modifier applied with `multiplier =` reach the states, and scale? (The deleted buttons
    applied them flat from JE scope; scaled country-scope is new.) Fallback: five banded
    fixed modifiers, as the stance uses — in which case the dashboard **still shows the
    exact index** and the tooltip names the band the trade effect is currently in; effects
    step, the reading does not. **Run 13 and 16 in a throwaway save before the phase-4 build,
    not during it**: 13 gates the whole trade channel and 16 gates all of 5b.
14. Does a **`script_only`** modifier type (`country_credit_standing_add`) work inside a
    treaty article's `source_modifier` / `target_modifier`? Laws and ranks are proven;
    treaties are not. The design routes the GDP-scaled terms through script anyway, so this
    only decides whether flat flavour terms can live in the article.
15. Does a treaty under `non_fulfillment = { consequences = freeze }` still iterate under
    `any_scope_treaty`? Decides whether a frozen peg still anchors.
16. `power_bloc ?= { modifier:power_bloc_shared_currency_bool = yes }` read from country
    scope — the vanilla precedent bool is only ever read by code.
17. `on_become_subject`: what is ROOT, and is `overlord` already valid inside it?
18. Cross-country reads in the monthly update (`var:te_mon_anchor = { var:te_policy_rate }`)
    see this month's or last month's value depending on country iteration order. The design
    tolerates either; confirm it is not something worse (a read of 0 mid-update).
19. ~~`participant_modifier`~~ **Answered on review (PR #340): zero vanilla uses** — it
    appears only in the two `.md` schema files. Avoid it.
20. `market_trade_reliance` (market scope, no target) — no vanilla script uses it; only its
    trigger-loc entry exists. Does it evaluate, and what range does a closed economy / an
    entrepôt actually read? Sets §15.3's three band edges. Fallback: drop the banding (×1.0).
21. Is `modifier:country_minting_add` readable in a subject's scope from script (§15A.4)?
    Same family as check 5.
22. **(6a / H6, the one 6a is waiting on.)** Does the vanilla AI **withdraw on its own** from an
    in-force treaty whose article `inherent_accept_score` has turned negative for it, once the
    binding period allows? Read it on a debug guarantor whose ward's `te_mon_lolr_calls` is set
    to 2 (`te_debug_monetary.11` option d), which puts `te_ai_backstop_repeat_defaulter` at −40
    against a base that was already negative. **If it does, 6a is complete as shipped**; if it
    does not, §15C.1 carries the fallback yearly walk on `NOT = { is_equal_exchange_for = root }`,
    monetary-only treaties, AI providers only — and that walk has its own sub-check, that a
    `withdraw = { country = root }` issued from a scripted effect on the yearly pulse fires
    `on_withdrawal` with `scope:withdrawing_country` set, as it does from an event option (P5-9).
23. **(6c.)** Does `contestion_type = control_target_country_capital` on a hostile *monetary*
    article resolve in the play UI? In-mod precedent (`105_enforce_privatization.txt`), so low
    risk — but 113 and 114 are the first articles to demand something that lives in script
    variables rather than in a state or a law.
24. **(6a / H5.)** How do repeated **same-name `target_modifier`s** from several in-force
    articles stack on one country? Read an anchor's prestige with two, then three, debug
    peggers: additive stacking shows +4% then +6%. Check 14's cousin, live again *because* the
    shipped prestige lines stay (H5). The fan-out is accepted by ruling, so this row **records
    the answer; it does not fail**. If prestige turns out to run away with headcount, §15C.1
    keeps the managed, GDP-scaled `te_mon_arrangement_prestige` term on record as the fix.

---

## 18. Deletions and save migration

> **Done** (phase 1). Both buttons and every live reference are gone; the
> `banking_policy_rate_hike` static modifier and its two loc keys stay defined for one
> release so the migration can run, and `common/scripted_effects/legacy_modifier_cleanup.txt`
> carries the dated checklist of the four artefacts that must be deleted together. The
> section below is kept as the record of what the deletion covered — line numbers predate the
> implementation.

### 18.1 Phase 1 — `cb_policy_rate_hike`

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

### 18.2 Phase 4 — `cb_fx_devaluation` / `cb_fx_support` (and `cb_fx_swap_lines` in 5a)

> **Done** (phase 4, 2026-09-21) for the devaluation / support pair — see §0.7. Both static
> modifiers and `te_mon_peg_devalued` stay defined for one release;
> `legacy_modifier_cleanup.txt` carries the dated checklist. `cb_fx_swap_lines` is untouched
> and still belongs to 5a. The survey below is kept as the record; line numbers predate the
> implementation.
>
> **Done** (phase 5a, 2026-09-21) for `cb_fx_swap_lines` as well — §0.8. The
> `banking_fx_swap_lines` static modifier stays defined for one release;
> `te_monetary_init_arrangement_variables` strips it every pulse and
> `legacy_modifier_cleanup.txt` carries its dated checklist. No state to migrate: the tool was
> a flat modifier, and its replacement is a treaty the country has to go and sign.

Surveyed 2026-09-20; line numbers are of that date. **Delete the two as a pair** (§15.5).

- `common/journal_entries/je_banking.txt:59-66`
- `common/scripted_buttons/timeline_extended_scripted_buttons.txt:394-492` — four buttons;
  the two survivors' `ai_chance` blocks do not reference them, but the disable-buttons
  cross-reference each other (`:438`, `:488`)
- `common/scripted_effects/banking_policy_effects.txt:97-184` (the FX half);
  `common/scripted_triggers/banking_policy_triggers.txt:129-149`;
  `common/scripted_triggers/market_triggers.txt:81-84` (`banking_tool_*_active`)
- `common/scripted_guis/banking_dashboard_scripted_gui.txt:286-317`;
  `gui/journal_entry_widgets/banking_dashboard_widget.gui:475-511,1615-1651`
- `common/scripted_guis/te_history_scripted_gui.txt:116-135` (marker rows; orphan marker
  vars in saves are harmless)
- `common/static_modifiers/extra_modifiers.txt:885-904`; `fx_support_activation_cost` at
  `common/script_values/extra_script_values.txt:1902`
- **Tech gates** — `country_can_use_fx_devaluation_bool` / `…_fx_support_bool`:
  `common/modifier_type_definitions/tech_gate_modifier_types.txt:284,304`; granted at
  `common/technology/technologies/era_6.txt:178` and `modified.txt:62-63`, both written by
  **`scripts/generators/add_tech_modifiers.py:258,263,289-291`** — edit the generator, not
  its output
  > **Correction (2026-09-21).** "Edit the generator, not its output" was wrong for
  > deletions, and following it is what made phases 4/5 edit both by hand. That script is
  > **additive only**: it appends missing definitions and never prunes, and
  > `tech_gate_modifier_types.txt` is hand-maintained (it also holds the space-program
  > block the script knows nothing about). Deleting a tech gate means removing it from the
  > script's tables **and** from the modifier-type file / tech files / loc — the table edit
  > alone only stops it being re-added. Adding a gate is still a one-place edit: put it in
  > the tables and run the script.
- **Law lock** `country_banking_lock_fx_devaluation_bool`:
  `common/modifier_type_definitions/banking_cycle_modifier_types.txt:71`, granted at
  `common/laws/extra_laws.txt:2348`
- `concept_currency_devaluation` (`common/game_concepts/extra_concepts.txt:17`) — **keep**,
  re-written to describe the §12.3 option and a weak float
- loc: `te_miscellaneous_l_english.yml` (≈25 keys, upper- and lower-case — `grep -i`), and
  **`te_concepts_l_english.yml:66-67,344-347,772,789-790`**, the easy ones to miss
- docs: `mod_systems.md` and `journal_entry_systems.md` § Banking Cycle tool tables

**Save migration**, same recipe as phase 1: keep both static modifiers defined for one
release; `extra_effects.txt:390-391` and `legacy_modifier_cleanup.txt:39-40` already strip
them, so extend that dated checklist rather than adding a new mechanism. A country holding
either modifier at load has its **index set directly** to 80 / 120 — what the ±0.25 modifier
*was*, in index points — and drifts to its own target from there. (Not a `te_fx_shock`: a
shock delivers 38% of its size, §15.1, so ±10 would swap a ±25% edge for ±5% overnight —
the lurch the migration exists to prevent.)
Phase 5a repeats the recipe for `cb_fx_swap_lines` / `banking_fx_swap_lines` (buttons
`:543-590`, triggers `:151-164`, modifier `:917-924`, its tech bool and law lock).

---

## 19. Phases

Each phase is playable alone. Later phases can be cut.

**Status.** Rows **1, 2, 3, 4, 5a, 5b, 5c, 6a, 6b and 6c are implemented** and pending in-game
verification (rows 5a–5c: [§0.8](#08-phase-5-as-shipped--rulings-deviations-and-open-checks),
checklist P5-1…18; row 4:
[§0.7](#07-phase-4-as-shipped--rulings-deviations-and-open-checks), checklist P4-1…12) — see
§0.1–§0.3, [§0.4](#04-phase-2-as-shipped--rulings-deviations-and-open-checks) and
[§0.5](#05-phase-3-as-shipped--rulings-deviations-and-open-checks); row 2's exit criteria are
§0.4 checklist items 24–25 and row 3's are §0.5 items 36–39. Row 3's "regime law stances" had
already shipped with phase 2 (§13 "Delivered"). Row 5 was scoped 2026-09-20 and built
2026-09-21 in the order 5a → 5c → 5b, one commit each, so each is still cuttable. (The table itself
carries no status column and is left as written.) Rows **6a–6c** were scoped, planned, ruled and
built on 2026-09-21, in one change rather than four
([§15C](#15c-phase-6-plan--leverage-coercion-and-exploit-hardening-built-2026-09-21) is the plan and
[§0.10](#010-phase-6-as-shipped--rulings-deviations-and-open-checks) the record; checklist
P6-1…13).

| Phase | Ships | Interim rule until the next phase | Exit criteria |
|---|---|---|---|
| **1** | country-scope plumbing (incl. `on_game_started`); both premium types + full §7.5 conversion + access/rank tables; target + drift; delegation + mandates (π terms dropped, §6); CBI binding; regime dial ranges; stance → cycle via the variable update; rate-hike deletion; dashboard block; history series | world/reference rate = `era_base`; gold standard target clamped to `era_base` ±2; inflation = 0; OMO usable at the floor but without its inflation cost | §17 checks 1–4 pass; anchor table (§7.4) reproduced in-game within 0.5pp; observer-mode run shows no country at the 60 cap, and none at the 0.5 *total* clamp, by accident; AI countries' stance tracks the cycle; **mean AI stance gap ≈ 0 outside cycle extremes** (no regime is permanently tight or loose); r\* cannot be read from any tooltip |
| **2** | inflation (core / headline / anchored expectations), basket, wage-pressure type + real-wage dividend, §10 formula, monetisation, QE costs, hyperinflation chain, §13 stance politics | gold standard still on the ±2 band | 50-year observer run: median fiat inflation 1–4% **including AI on the growth mandate** (at war or `scaled_debt ≥ 0.5`), no oscillation with period < 3 years, at least one organic hyperinflation and one deflation. **Debug harness**: a fiat tag pinned to a fixed manual target — observer runs never exercise the human path, because AI is always delegated; confirm the drift is slow (e-folding of years), that the §10 worked example reproduces, that **rate paid on the never-disinflate path never falls below the pre-war baseline** once expectations catch up (the §10 tuning invariant), and that its §9.2 band penalties make it worse *overall* over 15 years than disinflating — judged on treasury, SoL and radicals, not rate paid alone |
| **3** | real world rate (discretionary GPs only), gold flows + hot money, peg confidence, convertibility crisis; regime law stances | FX buttons unchanged | world rate sits at `era_base` in 1836 and does not drift on its own; a discretionary GP's hike visibly drains a small gold country; AI on peg defence survives a 2pp world-rate rise; holding world + 5 on gold yields no lasting treasury gain |
| **4** | §15: `te_fx_shadow` for everyone and `te_fx_index` by regime (float, metallic par, `te_fx_shock`), the overvaluation drain on a gold peg, world inflation (own share excluded), `te_fx_weak` / `te_fx_strong`, imported inflation inside cost-push, FX premium, `controls_damp` + capital-controls fatigue, dashboard row + history series; devalue/support deleted (§18.2), FX events re-pointed | no anchoring: a country that wants a peg has gold or nothing; `cb_fx_swap_lines` unchanged | §17 check 13 passes; the 1836 world sits at par and stays there; a fiat harness tag held 2pp loose settles at 92–94 within two years (§15.1 table); the 1836 gold world shows **no overvaluation drain at start** (a peg defender at a zero gap has shadow ≈ 100); a gold country that inflates 5pp above the world for three years loses its peg through the overvaluation term; in a 50-year observer run no floating AI country is pinned at 50 or 150 outside the hyperinflation band — **a statement about AI mandates (§20 risk 9), so a failure here is fixed in §6, not in the FX constants**; **the §10 invariant extended to phase 4: a fiat harness tag held at the loose clamp for 20 years ends worse on treasury, SoL and radicals than a neutral one *with the trade edge on*** (a 5pp loose stance is ~90% of `law_mercantilism`'s ±0.25 for no law — if this fails, halve the per-point value, §20 risk 10); and phase 2's median-inflation criterion **still holds with imported inflation on**; harness shock of −20 under price stability: headline back within 1pp of its pre-shock path in four years (§20 risk 9 converges); ten peacetime years of capital controls lands Industrialists and Petite Bourgeoisie at −5; a gold country under controls holding world − 4 drains like world − 1; all audits clean after the deletion and AI countries still use their remaining tools |
| **5a** | §15A.1–2: the anchored state (`te_mon_anchor`, kind; validity / discovery / yearly scan) on phase 4's shadow and overvaluation; `currency_peg`, `swap_line`, `lender_of_last_resort` articles; peg-crisis re-read; GDP-scaled arrangement modifiers; `cb_fx_swap_lines` deleted | blocs and subjects are monetary islands | §17 checks 14–15, 18 answered; an AI minor pegged to a GP tracks a 2pp anchor hike within two months and survives it; the same peg **breaks** under 15 points of sustained overvaluation; a GP's provider cost for a minor is < 10% of the minor's benefit; no chain or cycle of anchors can be constructed; AI signs pegs and swap lines in an observer run, and not universally |
| **5b** | §15A.3: `principle_group_monetary_union` (3 tiers), adoption action + convergence criteria, overvaluation premium, convergence pressure, exit | subjects still islands | §17 checks 16, 19 answered; an adopter in a slump while the leader runs hot shows a visibly rising premium and a tight band; the **exit invariant** holds in the harness (worse than staying for ≥ 5 years at 15 points of overvaluation, better after); a pressed, debt-heavy adopter costs a tier-3 leader a backstop call within a cycle or two; pressing a bloc of refusers loses the leader cohesion on net; a human holdout sees *The Question* fewer than ~6 times a campaign |
| **5c** | §15A.4: automatic currency boards for `autonomy_level = 1` subjects, seigniorage transfer, wrong-stance liberty desire | — | §17 check 17 answered; a puppet's rate tracks its overlord's within a month of subjugation and returns to its own rule within a month of release, with no exit penalty; the overlord's minting gain is GDP-scaled (a tiny puppet is a rounding error); a sustained 2pp wrong stance moves liberty desire measurably but does not alone cause a revolt |
| **6a** *(§15C.1 / §0.10)* | the swap line as a repayable, capped, single-provider loan drawn only in a *financial* crisis; the guarantee's call counter (honour cost, relief, AI odds, cooldown) read by the signing score too; the AI's own post-signing withdrawal on the re-scored articles (a scripted yearly walk only as fallback); `non_fulfillment = withdraw` on war / expulsion. Prestige stays as shipped (H5) | — | P6-1…9; P5-5, P5-7 and P5-9 still hold |
| **6b** *(§15C.2 / §0.10)* | `country_treaty_leverage_generation_add` 200 / 150 / 300 on the three articles — shipped on the strong side, **corrected 2026-09-21** to the dominated party's block (the modifier generates leverage *against* its carrier; see §15C.2) | — | P6-10 |
| **6c** *(§15C.3 / §0.10)* | `imposed_currency_peg` and `debt_receivership`: hostile, enforceable, demandable only against a country in default; no hostile swap line | — | P6-11…13: both rare in a 50-year observer run, and the friendly three still signed |

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
3. **INJECT semantics.** *Retired 2026-09-20:* the §17 gate was run and INJECT sums in
   every shape the mod uses, so the per-axis fallbacks are recipes, not pending work.
4. **Variable lifecycle** — unguarded `immediate` resets; a multiplier-backing var removed
   by a cleanup effect; a national-bank country with no JE and therefore no dial.
   *Mitigation:* single owner on the country pulse, guards everywhere, never remove,
   auto-delegate the JE-less.
5. **Feedback instability** — inflation → rate → cycle → inflation; a circular world rate;
   one-month lags between pulses. *Mitigation:* clamps on the stance gap and cost-push;
   seeded averages; bankless GPs excluded from the world rate; history charts of rate and
   inflation as the oscillation detector in observer runs.
6. **Never disinflating is the cheapest line** if the deterrents are under-sized: adaptive
   expectations lag an accelerating inflation indefinitely, so debt erosion never reverses.
   *Mitigation:* the §10 tuning invariant (unanchored premium + §9.2 bands incl. minting
   collapse + lenders' floor exceed the lag above ~10%), checked on the accelerating path
   with the phase-2 harness.
7. **Free money from the peg** — a rate held far above the world rate pulls in gold with no
   counterparty. *Mitigation:* hot-money balance, reserve cap, price–specie flow (§12.2).
8. **The neutral rate is learnable** if its random component is too small, making the
   hidden-information decision hollow. *Mitigation:* tune the walk first; keep the band
   driven by the estimate, not the truth.
9. **The depreciation spiral** (phase 4) — weak currency → imported inflation → higher
   expected inflation → weaker currency, plus weak currency → premium → weaker currency.
   Both are positive feedback. *Mitigation:* imported inflation is a change term under the
   shared ±6 clamp and fades at 1/36; the premium loop's gain is 0.075; step 5 reads last
   month's index; the index is clamped 50–150. **The loop gain is computable** (derived on
   review, PR #340; confirm with the harness): per pp of expected inflation `fx_target`
   moves `4·(1 − ρ) + 2 + ~0.4` points — the carry term, cancelled to the extent ρ (the
   mandate's rate response) tracks expectations 1:1; the confidence term; the unanchored
   premium through the ×1.5 term — and the return leg (index → imported inflation →
   expected) is ≈ `0.1 × (1 − c)`. Round trip ≈ **0.14 at ρ = 1, c = 0.4; 0.5 at ρ = 0,
   c = 0.2; < 0.65 at worst** — under 1 everywhere, without leaning on the clamps. But it is
   dominated by ρ: the spiral is a *policy-failure* signature (a fixed manual dial, a growth
   mandate, a no-dial regime), which is realistic and intended. The phase-4 harness shock is
   the test, and the FX history chart the detector.
10. **The trade edge is large and universal** (phase 4). ±1.25% per point on every state of
   every floating country is a bigger aggregate lever than two AI-only buttons ever were,
   and world-market effects of many countries drifting at once are untested. *Mitigation:*
   §17 check 13 first; halve the per-point value before touching the formula.
11. **Anchoring is a way to dodge the system** (phase 5) — peg to a credible neighbour,
   import its rate and credibility, ignore inflation. *Mitigation:* own inflation and bands
   keep running; overvaluation drains confidence or raises the premium; no monetisation.
   Exit criterion: a pegged country that inflates must end worse off than a floater that does.
12. **No counterparty ever signs** (phase 5) if provider costs are mirrored. *Mitigation:*
   the GDP-ratio rule (§15A.1), and the reserve-currency premium cut as a standing reason to
   be an anchor.
13. **The arrangements can be gamed deliberately, not just stumbled into by the AI** (phase 5,
   found on review — §15B): a recipient can hold several swap-line providers at once and farm
   a self-inflicted external crisis against them; a ward can serial-default every five years
   against a guarantor whose Honour/Renege odds don't move with history; an anchor can take
   unlimited peggers for a flat per-article prestige gain no cap touches. *Mitigation:*
   **built 2026-09-21** — §15C.1 / §0.10 (H1–H7): the draw is a repayable, capped loan from one
   provider, drawn only in a financial crisis; the guarantee remembers its calls in the cost,
   the relief, the AI's odds, the cooldown and the signing score. The third item — the pegger
   fan-out — is **accepted as shipped by owner ruling H5**; §17 check 24 records how it stacks.
   Two things are still open in play rather than in script: §17 check 22 (does the engine's own
   AI actually withdraw on the re-scored articles, or is §15C.1's fallback walk needed?), and
   the fact that none of the phase-5 numbers these schedules move has been watched settle yet
   (§0.8's P5-1…18 are unrun).
14. **Coercive articles make the AI world grabby** (phase 6c, built — untested) — every
   domineering great power demanding pegs and receiverships in every play. *Mitigation:* the
   `in_default` pretext (ruling C4), tested symmetrically in `possible` and directionally in
   `can_ratify` (§0.10 P7); `evaluation_chance` 0.01, and `request`-only usage; the
   don't-impose-on-friends rule. P6-13's rarity criterion is the exit test, and the two
   articles are the first thing to cut — they are two self-contained files plus the
   `OR = { has_type … }` edits §15C.3 lists.

---

## 21. Tuning constants

| Constant | Start | § |
|---|---|---|
| Drift per month | 1/3 pp (2/3 digital) | 4 |
| Target range: gold / fiat / digital | 0–15 / 0–25 / −3–25 | 5 |
| Target range: commodity money with a bank (`te_mon_commodity_band_margin_down` / `_up`; centre hysteresis `te_mon_commodity_centre_hysteresis`) | `centre − 1` to `centre + 3`, floored at 0; centre = `round(world)`, re-rounded at 0.75 | 5.1, 0.6 |
| Commodity price-specie term (`te_mon_commodity_specie_tolerance` / `_per_pp` / `_clamp`) | tolerance 1pp of core above world inflation, then −2pp of pressure per pp, clamped at −6 | 9.1, 0.6 R7 |
| Bankless spread | 1.0 | 5 |
| Administered rate (command) | 3.0 | 5 |
| Rate-paid clamp | 0.5 – 60 | 4 |
| Structural premium floor (CBI); cyclical added after it | 0.5 (0.25) | 7 |
| Rank: decentralized | +10 | 7.3 |
| Mod techs (structural) | **−0.3 ×4, −0.15** = −1.35 (was −0.4 ×4, −0.2 = −1.8), re-homed 2026-09-20 to `keynesian_economics` (6), `computer_networks` (8), `knowledge_economy` (9), `machine_learning` (10, the −0.15) and `universal_digital_identity` (11); the last two also carry `country_credit_standing_floor_add` −0.1pp each, so the floor goes 0.5 → 0.3 (CBI 0.25 → 0.05) | 7.5 |
| Delegated target rounding / hysteresis | integer / 0.75 | 4 |
| Gold / CBI credibility | −1.0 / −0.5 | 5 |
| `_mult` → pp conversion | × 20 | 7.5 |
| Access base / techs / no exchange | +8 / −4, −2.5, then **−0.25, −0.5, −0.75** (eras 3–5; was −0.5 ×3 — back-loaded 2026-09-20; the first two cannot move without moving §7.4's 1836 rows) / +2 | 7.2 |
| Rank table | 0.5 · 1 · 2 · 3 · 4 · 6 · 8 | 7.3 |
| Debt-load premium | 0 → +4 over `scaled_debt` 0.25 → 1.0 | 7.6 |
| Stance per pp: momentum / bubble / pool | 0.125 / 0.75 / 0.01; gap clamp ±4 | 8 |
| Neutral rate: era base / growth coeff / walk | 3 → 2 / 0.25 / ±0.1 | 8 |
| Estimation error (CBI) | ±1.5 (±0.5) | 6 |
| Price-stability mandate: inflation weight / target | 1.0 / 2% | 6 |
| Growth mandate: bias / reaction / threshold | −1.0 / 0.5 / 4% | 6 |
| Inflation pressure (pp): stance per pp / phases / bubble / deficit / monetisation / QE | 0.4 / ±0.3–1.5 / 0.2 / 0.3 / 2.5 / 1.0 | 9.1 |
| Core adjustment speed | 0.10 per month | 9.1 |
| Expectation α: manual, delegated (CBI) | 1/24 (1/12) | 9.1 |
| Credibility anchor c: state-owned banking / manual / delegated / CBI / gold | 0.15 / 0.25 / 0.4 / 0.7 / 1 | 9.1 |
| De-anchoring span (c_eff → 0) | 10pp from target | 9.1 |
| Specie-flow pressure | 0.5pp per 1% of GDP per year of gold flow | 9.1, 12.2 |
| Minting collapse: very high / hyper / dollarised | −0.3 / −0.8 / −0.75 | 9.2 |
| Crypto minting **(proposed)** | −0.75 | 5.1 |
| Basket: k / avg α / headline clamp | 0.3 / 1/36 / ±6pp | 9.3 |
| Real-wage dividend: momentum per +0.1pp wage pressure | +0.03 | 9.4 |
| Hyperinflation threshold | 50% | 9.2 |
| Lenders' floor | `era_base` + expected | 10 |
| Monetisation per level: minting / pressure / premium | 1% GDP/yr (baseline minting ≈ 5.2%) / +2.5pp / +0.5 | 11 |
| Gold flow per pp / gap clamp / hot-money exit speed / inflow cap | 0.002 × GDP per month / ±5 / ×2 / the **bank's vault** at its limit (`te_bank_gold` = 0.2 × GDP — §0.5 "The bank's own reserve"; was the treasury's `scaled_gold_reserves` 1) | 12.2 |
| Peg crisis threshold | confidence ≤ 20 | 12.3 |
| World / reference rate fallback | `era_base` | 12.1 |
| World rate clamp (ruling Q1) | −2 – 10 | 12.1 |
| Peg-defence reserve shortfall (ruling Q5) | 2pp with the bank's vault empty → 0 at half its limit (treasury debt no longer counts); the mandate adds half, rounded **up to a tenth** | 6 |
| Target step: click / ctrl / shift | 1pp / 0.1pp / to the regime limit | 4 |
| Hot-money exit floor (ruling Q7) | a 0.5pp gap (Q8's hot-money cap was retired by the hybrid model) | 12.2 |
| Vault: limit / seed floor / recapitalisation step / AI top-up rule | 0.2 × GDP / 0.5 of the limit / 0.1 of the limit / vault < 0.25 and treasury > 0.5 | 0.5, 12.2 |
| Peg confidence: start / healthy recovery / crisis cooldown (ruling Q10) | 100 / +1 a month / 24 months | 12.3 |
| Defend / Suspend / Devalue | world + 4 for 12 months, +40 · 60 months, +2pp premium 5y, credibility lost 10y · confidence 50, revaluation 15% of the reserve limit, +3pp pressure decaying over 2y | 12.3 |
| FX target: per pp real-rate gap (clamp) / per pp inflation gap (clamp) / per pp cyclical premium | 4.0 (±5) / 2.0 (±10) / 1.5 | 15.1 |
| FX adjustment speed / index clamp / shock clamp + decay / shock capture | 1/12 per month / 50–150 / ±40, ×11/12 / 38% of nominal | 15.1 |
| Post-devaluation: index / return speed / window (replaces Q12's ±0.15 over 5y, same peak and impulse) | 88 / 1/30 / 60 months | 15.2 |
| Overvaluation drain on a peg (gold, and 5a) | −1 confidence per 2 points over 5, × `controls_damp`; counts as pressure for Q10 | 15.2 |
| Imported-inflation openness bands (`market_trade_reliance`) | ×0.6 / ×1.0 / ×1.5 at < 0.1 / 0.1–0.3 / > 0.3 | 15.3 |
| Trade edge per index point (export / import) | ±0.0125 | 15.3 |
| FX premium | +0.05pp per point below par | 15.3 |
| Imported inflation: k / avg α | 0.15 / 1/36 (inside the ±6pp cost-push clamp) | 15.3 |
| `controls_damp` | 0.25 | 15.4 |
| Controls fatigue: approval / pool drag / cap / decay when lifted | −1 and −0.02 per 12 months / 5 steps / 3 months per month | 15.4 |
| Anchor spread: peg / board / bloc | 0.5 / 0.25 / 0 | 15A.1 |
| Imported credibility | `max(own c, 0.8 × anchor c)` | 15A.1 |
| Peg: premium cut / reserve-currency cut | −0.5pp / −0.1pp per 5% world GDP, cap −0.5 | 15A.2 |
| Swap line: confidence / premium / crisis draw | +2 per month / −1pp / 0.1% recipient GDP per month | 15A.2 |
| LOLR: debt-load premium / honour cost / renege suspension | ×0.5 / 5% ward GDP / 5 years | 15A.2 |
| Provider cost scaling | recipient benefit × clamp(recipient GDP ÷ provider GDP, 0, 1) | 15A.1 |
| Union: convergence (inflation / debt) / overvaluation premium / trade | 3pp / `scaled_debt` < 0.5 / +0.1pp per point over 5 (×0.5 at tier 3) / +0.05 | 15A.3 |
| Union pressure: refusal's leverage resistance / event floor | +250 for 10 years, refreshed / once per 5 years, state-change triggered | 15A.3 |
| Union exit: premium / re-adoption lock | +3pp decaying over 10 years / 10 years | 15A.3 |
| Currency board: subject minting / overlord's share / wrong-stance threshold | −0.5 / half the subject's minting, as a flat add / stance band 1 or 5 for 6 months | 15A.4 |
| Swap line as a loan **(6a, shipped; numbers still proposed)**: limit / repayment / crisis definition | 2% of recipient GDP outstanding / 0.1% of GDP a month out of crisis, settled in one lump when the line ends / `te_mon_in_financial_crisis` (no war leg) | 15C.1 |
| LOLR call counter **(6a, shipped; numbers still proposed)**: honour cost / relief share / AI odds / cooldown / forget | 5% × (1 + 0.5n), cap 15% / 0.5 · 0.35 · 0.2 · 0 / Honour 10 − 3n : Renege 2 + 2n / 60 × (1 + n) months / one call per 120 quiet months | 15C.1 |
| AI post-signing withdrawal **(6a, H6, shipped)** | the engine's own, on `inherent_accept_score` with −20 per ward call and −20 if drawn. **The fallback walk is deliberately unwritten** until §17 check 22 says it is needed | 15C.1, 0.10 |
| Treaty leverage **(6b / 6c, shipped; numbers still proposed)** | peg 200 / swap 150 / LOLR 300 / imposed peg 400 / receivership 500 | 15C.2, 15C.3 |
| Imposed peg / receivership **(6c, shipped; numbers still proposed; pretext ruled C4)** | spread 1.0, no standing cut, −10 legitimacy, infamy base 8 / take 0.1% of debtor GDP a month, −10 legitimacy, infamy base 10, self-ends 12 months after `scaled_debt` < 0.25 / both demandable only against a country `in_default` | 15C.3 |

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
