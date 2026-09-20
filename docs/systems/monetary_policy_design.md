# Monetary Policy — Design

> **STATUS: PHASES 1–3 IMPLEMENTED, PENDING IN-GAME VERIFICATION.** Phase 3 (§19 row 3 — the
> real world rate, gold flows and hot money, peg confidence, the convertibility crisis)
> shipped on `feat/monetary-policy-phase3` on 2026-09-20; see
> [§0.5](#05-phase-3-as-shipped--rulings-deviations-and-open-checks). Phase 2
> (§19 row 2 — inflation, monetisation and QE costs, the §9.2 bands and hyperinflation
> chain, wage pressure, §13 stance politics) shipped on `feat/monetary-policy-phase2` on
> 2026-09-20 and has not been seen in a running game either; see
> [§0.4](#04-phase-2-as-shipped--rulings-deviations-and-open-checks). Phases 4–5 are
> still design only. Written 2026-09-19 from a design
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
once; `banking_stance_band_3` is an empty modifier with no icon (the offset that used to read
"−20.0%" beside the rate it cancels is gone — the cancel moved into `INJECT:base_values`);
`pm_shell_pernis_refinery`'s structural term is `workforce_scaled`, so §7.5's "−0.3" is only
true at one building level; `cb_fx_support`'s `banking_stance_is_tight` easing weight may be
sign-wrong and belongs to the phase-3 FX pass; the band swap does not self-heal if a JE's
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
| **T7** | Rural Folk: `cross_of_gold_currency` added to `ideology_isolationist` | `ideology_particularist` already carried `simple_currency`, which cancelled the Cross of Gold on `ideology_agrarian` **exactly**, so §13's marquee row netted zero on gold and zero on fiat. Isolationist is a Rural Folk baseline held by no other IG, and the gold standard is unlocked by `international_exchange_standards` — an international order is what an isolationist objects to | one line of generator input |
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
| Credit standing + risk premium | exact, each with a per-source breakdown tooltip | `te_premium_structural`, `te_premium_cyclical` (§7) |
| Inflation / expected inflation (P2) | exact, 1 decimal | `te_inflation`, `te_inflation_expected` |
| **Policy stance** | **band only**: very loose / loose / neutral / tight / very tight | the bank's *estimate* of (real rate − neutral rate) |
| World rate (P3) | exact (a **real** rate) | `global_var:te_world_rate` |
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
policy_rate   drifts toward target at 1/3 pp per month     has a dial: national bank on gold / fiat / digital
              = world_rate + expected_inflation + 1.0       no dial: no national bank, or commodity money /
                                                            crypto with or without one
              = administered_rate                           command economy

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

- **Dial:** integer target, 1pp steps, range by regime (§5). Drift 1/3 pp per month
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
| `law_commodity_money` | **none**, even with a national bank | pays world rate + spread | no monetisation, no QE; expected inflation pinned to 0 |
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

This gives each law a real identity: gold buys credibility and cheap borrowing at the price of autonomy; fiat buys
autonomy and war finance at the price of discipline; crypto is commodity money again with
better trade modifiers.

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
| **Hand-judged:** `institution_national_bank` | −0.05 / level | **−0.3 / level** (×20 would be −5pp at level 5) |

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
chose. A market rate clears at neutral by definition, so bankless, commodity-money, crypto
and command-economy countries get **stance gap = 0**. The same logic sets the interim
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
have national banks but are on commodity money, so they have no dial and pay world +
spread. Averaging all three would define the world rate in terms of itself (and ratchet it
up by the spread every month). With none of them discretionary the world rate is
`era_base` — until a player Britain takes the dial, or a fiat great power appears, and
starts moving it for everyone else.

It is real because capital responds to real returns: a fiat GP at 10% inflation and a 13%
policy rate must not force gold countries to 13%. A gold country's gap is
`policy − world` directly (its expected inflation is 0); a no-dial country pays
`world + own expected inflation + 1`.

Computed on the global `on_monthly_pulse` with two accumulator globals (Σ gdp/10⁶ × real
rate, Σ gdp/10⁶ — the scaling is fixed-point headroom), seeded in `te_init_global_state`
(`common/on_actions/extra_on_actions.txt:22-31`).

Effect: a small country is pulled around by the hegemon's central bank.

### 12.2 Gold flows

Gold-standard countries with a national bank only:

```
gap  = clamp( policy_rate − world_rate , −5 , +5 )
flow = gap × 0.002 × gdp          per month; positive = inflow
```

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
| **Devalue the peg** | one-off gold reserve revaluation + export boost; confidence reset to 50; infamy and GP relations (the costs the old *Devalue* button carried); expected inflation +3 |

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

### 15.1 International monetary arrangements — to scope (phase 5)

Not designed; recorded so it is not forgotten. Phases 1–4 treat every country as a monetary
island apart from the world rate. The mod's diplomatic layer should eventually carry
monetary content of its own — look into, and hopefully implement:

- **Treaty articles** — e.g. a currency peg to a partner, swap lines or a standing credit
  facility, a lender-of-last-resort guarantee, reserve pooling; each with a real cost to the
  stronger party (shared risk premium, imported stance).
- **Subjects** — a subject using the overlord's currency or pegged to it: it inherits the
  overlord's policy rate and credibility and gives up its own dial (a currency board);
  colonial-era monetary dependence as a lever for both sides.
- **Power blocs** — a principle (or tier) for a **shared currency**, à la the euro, available
  to fiat / digital members: one policy rate set for the bloc (by the leader, or weighted by
  GDP), a common credibility bonus and lower intra-bloc transaction costs, against the loss
  of the dial — a member in a slump while the bloc runs hot gets the wrong stance, cannot
  devalue, and its risk premium becomes the adjustment valve (the euro-crisis shape). Exit
  should be possible and expensive.

Design principle as elsewhere (§1): each arrangement must be a genuine tradeoff, and any
asymmetry between members should come from shared mechanics (size, credibility, cycle
position), not from special-casing. Depends on phase 3 (world rate) and largely on phase 4
(exchange rates); the currency-union open question above belongs here.

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

---

## 18. Deletions and save migration

> **Done** (phase 1). Both buttons and every live reference are gone; the
> `banking_policy_rate_hike` static modifier and its two loc keys stay defined for one
> release so the migration can run, and `common/scripted_effects/legacy_modifier_cleanup.txt`
> carries the dated checklist of the four artefacts that must be deleted together. The
> section below is kept as the record of what the deletion covered — line numbers predate the
> implementation.

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

**Status.** Rows **1, 2 and 3 are implemented** and pending in-game verification — see
§0.1–§0.3, [§0.4](#04-phase-2-as-shipped--rulings-deviations-and-open-checks) and
[§0.5](#05-phase-3-as-shipped--rulings-deviations-and-open-checks); row 2's exit criteria are
§0.4 checklist items 24–25 and row 3's are §0.5 items 36–39. Row 3's "regime law stances" had
already shipped with phase 2 (§13 "Delivered"). Rows 4–5 are design only. (The table itself
carries no status column and is left as written.)

| Phase | Ships | Interim rule until the next phase | Exit criteria |
|---|---|---|---|
| **1** | country-scope plumbing (incl. `on_game_started`); both premium types + full §7.5 conversion + access/rank tables; target + drift; delegation + mandates (π terms dropped, §6); CBI binding; regime dial ranges; stance → cycle via the variable update; rate-hike deletion; dashboard block; history series | world/reference rate = `era_base`; gold standard target clamped to `era_base` ±2; inflation = 0; OMO usable at the floor but without its inflation cost | §17 checks 1–4 pass; anchor table (§7.4) reproduced in-game within 0.5pp; observer-mode run shows no country at the 60 cap, and none at the 0.5 *total* clamp, by accident; AI countries' stance tracks the cycle; **mean AI stance gap ≈ 0 outside cycle extremes** (no regime is permanently tight or loose); r\* cannot be read from any tooltip |
| **2** | inflation (core / headline / anchored expectations), basket, wage-pressure type + real-wage dividend, §10 formula, monetisation, QE costs, hyperinflation chain, §13 stance politics | gold standard still on the ±2 band | 50-year observer run: median fiat inflation 1–4% **including AI on the growth mandate** (at war or `scaled_debt ≥ 0.5`), no oscillation with period < 3 years, at least one organic hyperinflation and one deflation. **Debug harness**: a fiat tag pinned to a fixed manual target — observer runs never exercise the human path, because AI is always delegated; confirm the drift is slow (e-folding of years), that the §10 worked example reproduces, that **rate paid on the never-disinflate path never falls below the pre-war baseline** once expectations catch up (the §10 tuning invariant), and that its §9.2 band penalties make it worse *overall* over 15 years than disinflating — judged on treasury, SoL and radicals, not rate paid alone |
| **3** | real world rate (discretionary GPs only), gold flows + hot money, peg confidence, convertibility crisis; regime law stances | FX buttons unchanged | world rate sits at `era_base` in 1836 and does not drift on its own; a discretionary GP's hike visibly drains a small gold country; AI on peg defence survives a 2pp world-rate rise; holding world + 5 on gold yields no lasting treasury gain |
| **4** | FX index, trilemma, capital-controls politics; devalue/support deleted | — | — |
| **5** | *(to scope — §15.1)* international monetary arrangements: treaty articles, subject currency dependence, power-bloc shared currency | — | — |

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

---

## 21. Tuning constants

| Constant | Start | § |
|---|---|---|
| Drift per month | 1/3 pp (2/3 digital) | 4 |
| Target range: gold / fiat / digital | 0–15 / 0–25 / −3–25 | 5 |
| Bankless spread | 1.0 | 5 |
| Administered rate (command) | 3.0 | 5 |
| Rate-paid clamp | 0.5 – 60 | 4 |
| Structural premium floor (CBI); cyclical added after it | 0.5 (0.25) | 7 |
| Rank: decentralized | +10 | 7.3 |
| Mod techs (structural) | −0.4 ×4, −0.2 (era 12) | 7.5 |
| Delegated target rounding / hysteresis | integer / 0.75 | 4 |
| Gold / CBI credibility | −1.0 / −0.5 | 5 |
| `_mult` → pp conversion | × 20 | 7.5 |
| Access base / techs / no exchange | +8 / −4, −2.5, −0.5 ×3 / +2 | 7.2 |
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
| Gold flow per pp / gap clamp / hot-money exit speed / inflow cap | 0.002 × GDP per month / ±5 / ×2 / `scaled_gold_reserves` 1 | 12.2 |
| Peg crisis threshold | confidence ≤ 20 | 12.3 |
| World / reference rate fallback | `era_base` | 12.1 |
| World rate clamp (ruling Q1) | −2 – 10 | 12.1 |
| Peg-defence reserve shortfall (ruling Q5) | 2pp at zero reserves or in debt → 0 at half the limit; the mandate adds half, rounded **up to a tenth** | 6 |
| Target step: click / ctrl / shift | 1pp / 0.1pp / to the regime limit | 4 |
| Hot-money exit floor / hot-money cap (rulings Q7, Q8) | a 0.5pp gap / one reserve limit | 12.2 |
| Peg confidence: start / healthy recovery / crisis cooldown (ruling Q10) | 100 / +1 a month / 24 months | 12.3 |
| Defend / Suspend / Devalue | world + 4 for 12 months, +40 · 60 months, +2pp premium 5y, credibility lost 10y · confidence 50, revaluation 15% of the reserve limit, +3pp pressure decaying over 2y | 12.3 |

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
