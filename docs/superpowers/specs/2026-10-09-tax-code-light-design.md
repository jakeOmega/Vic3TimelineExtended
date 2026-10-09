# Light tax code: a fourth option on the tax code rule (design note)

**Date:** 2026-10-09 · **Status:** draft for the owner's check · **Base:** `main` at 7bbf8c8

Light mode is a separate option on `te_tax_code_rule`, `te_tax_code_light`. The full mode is not
changed. The vanilla taxation law stays enacted and sets each tax's range. Inside that range the
player moves each rate one step at a time from the tax code's panel, and the change applies at
once. There are no bills, debate, offers, promises, obligations, packages or sunsets.

## 1. Collection: the law stays, the tax level follows the heaviest tax

The law's own rates can't be switched off. The engine adds its `tax_modifier_<level>` rates to
whatever else carries a `tax_*_add`. So light mode collects the code's rate as **the law's rate
at the native tax level, plus a relief**:

- **The native tax level is derived, not chosen.** Each tax sits on a rung of its law's ladder:
  the lowest native level whose rate is at least the code's rate (a rate between rungs rounds up).
  The country's tax level is the highest rung among the taxes the law levies. The light sync sets
  it with `set_tax_level`. Vanilla's tax-level statics (legitimacy +10 … −20, radicals, expected
  SoL) therefore track the heaviest tax. A code with every tax on the same rung is vanilla exactly.
- **Relief is a country static modifier per tax**, `te_tax_light_relief_<key>`, one step's rate
  below zero, applied with `multiplier =` the number of steps the code sits below the law's rate
  at that level. Because the level is the highest rung, no tax sits above it, so relief is never
  positive.
  - Vanilla precedent: Montenegro's `mon_ease_taxes` is a country modifier with
    `tax_income_add = -0.04` and `tax_consumption_add = -0.02`
    (`common/static_modifiers/montenegrin_modifiers.txt:309`, applied in
    `montenegro_events.txt:1782`).
  - Statics, not amendments: no sponsor group is needed, a law change doesn't drop them, and a
    remove-and-add of one name is idempotent. Full mode's one-sync-a-day guard exists because of
    possible duplicate amendments, so light mode doesn't need it and a click applies the same day.
- **Why the heaviest tax, not the average.** With the average, a Proportional code could tax
  wages at 30% (very high) and dividends and consumption at their floors, and pay only the *low*
  level's price (+5 legitimacy instead of −20). Light mode would then beat vanilla at its own
  trade-off. With the heaviest tax, a lower rate on some taxes always costs revenue. What it buys
  is the goodwill of the groups that pay those taxes (§4).
- **The player's tax-level buttons are greyed** under any mode, because the rows set the level.
  The consumption-goods buttons stay live in light mode (§3), so `te_tax_native_controls_sgui`
  splits into a tax-level gate (any mode) and a goods gate (full mode only).
- **First in-game check:** the Budget panel's wage line under a Proportional law at *high*, with
  two steps of wage relief, should read 20%.

## 2. When the law changes: clamp

The hook that re-asserts the carrier in full mode (`te_tax.5`) becomes clamp-and-sync in light
mode:

- Each tax clamps into the new law's range.
- A tax the new law doesn't levy goes to 0.
- A tax it newly levies starts at the new law's rate at the current tax level, which is what
  enacting that law gives in vanilla.

The derived level is therefore unchanged unless a clamp moves the heaviest tax. Vanilla's
law-change approval already prices the switch, so the clamp scores no reaction of its own. The
bounds are generated from `MIGRATION` in `gen_tax_code.py` as
`te_tax_light_min/max_<key>` per law (`test_tax_code_migration.py` already pins that table to
`vanilla_parsed`).

## 3. Scope: consumption rate in, goods and customs out

- **In:** the consumption *rate*. All five laws levy it on the same 15–35% ladder.
- **Out (stay native):** the taxed-goods list, since no law bounds it and holding it would mean
  rebuilding goods drafting without a bill; customs, which are experimental even in full mode;
  relief provisions; history; estimates.
- **No light-customs option.** Light mode is a single option.

## 4. Interest groups

- **Standing view: vanilla's own.** The law is enacted, so the engine already gives every group
  its `IG_APPROVAL_FROM_LAW` stance approval. The view bands (`te_tax_ig_view_<ig>_<band>`) exist
  to reproduce that approval when the carrier displaces the law, and `te_tax_code_equivalent_*`
  need the carrier. So in light mode they are 0 by construction. Applying them as well would count
  the law twice. **"Keep the view bands" therefore means: unchanged in full mode, off in light
  mode.** Please confirm.
- **A reaction to each change.** Each step is scored per group with full mode's reasons, for that
  step alone: material `−10 × exposure × Δlevels` and ideology `stance lean × Δprogressiveness ×
  5`. The score goes into a per-group accumulator, `te_tax_lr_<ig>`. One country static per group,
  `te_tax_light_react_<ig>` (`interest_group_ig_<ig>_approval_add`), carries the rounded
  accumulator as its multiplier. It is refreshed at each change and by the monthly processor,
  which also decays the accumulator by about 30% a month (−5 fades in about six months).
  - A banded variable avoids the open question of whether re-adding a timed modifier stacks or
    refreshes.
  - A revolution's winner keeps the variable, and the next sync re-adds the modifier.
- **Size: a change is an action, so it sits in the law-change range.** Approval = score ÷ 4, so
  sweeping one tax across its whole range (four rungs) costs a fully exposed group −10, which is
  vanilla's `IG_APPROVAL_FROM_RADICAL_LAW_CHANGE`. The accumulator is capped at ±10.

  | Change (material reason only) | Group (exposure) | Approval |
  |---|---|---|
  | Proportional wage 20% → 22.5% (one step) | Trade Unions (1.0) | −1.25 |
  | Proportional wage 10% → 30% (whole range) | Trade Unions (1.0) | −10 |
  | Graduated wage 10% → 20% (whole range, half the width) | Trade Unions (1.0) | −5 |
  | Consumption 15% → 35% | Trade Unions (0.8) | −8 |
  | Graduated dividends 10% → 30% | Industrialists (1.0) | −10 |

- **Proposal: cuts count half.** A positive step score is halved. Raising a tax and cutting it
  back then nets a cost, so the reaction can't be pumped before an election. This is a call on
  how a cut is received in the fiction, so it's yours to make.

## 5. The AI: it keeps vanilla's tax level, and the code follows it

The AI keeps choosing its native tax level as in vanilla; nothing pins it. If the light sync finds
the level differs from the level the code last derived, something outside the code moved it: the
AI, vanilla's law-negotiation option or an event. The code then adopts what the game now
collects:

- Each tax moves by its law's difference between the two levels, clamped to the range.
- That change is scored for reactions exactly like a player's.

Results:

- An AI's code stays uniform, so it never carries relief and collects vanilla's rates. Its tax
  level is never fought, unlike under full mode's pin.
- There is no new AI fiscal logic to tune.

**Alternative (your suggestion):** raise one step within the range after three months of deficit
and cut one after six months of surplus. The tax to move would be picked by
`te_tax_ai_cost_<key>`, the politically cheapest. That needs the level pinned against the AI
again and a second fiscal brain beside vanilla's. I'd hold it back unless observer runs show the
vanilla level doing badly under light mode.

## 6. Cooldown: none

Vanilla's tax level has none. The brake is the reaction: it accumulates, and cuts count half.

## 7. Gates (task 2)

- `te_tax_code_full` takes today's body: either enabled option.
- `te_tax_code_light` is the new option.
- `te_tax_code_on` becomes "either". All three triggers are written positively.

Every existing `te_tax_code_on` site moves to `te_tax_code_full` (the generator for generated
files), so the bill machinery, AI bill loop, carrier, 130 amendments, vanilla-law gates, the
`te_tax.3` carrier install and the `te_tax.5` re-assert stay full-only. A short list then becomes
"either" or light:

- the journal entry's `is_shown_when_inactive`, the Budget tab and the entry unlock;
- the migration fan-out (light: rates from law and level, no `activate_law`);
- the tax-level button gate;
- the sync dispatch.

Sites that would be wrong if left widened, all moved to full:

- `te_demog_values.txt:221` would count Graduated twice;
- the three Cultural Hegemony "taxation is never pressed" checks, which are false in light mode;
- the goods buttons;
- the spectrum auction, which in light mode adds its +1 point of dividends as in vanilla.

## 8. GUI (task 3)

In light mode the Tax Code tab and the entry show:

- the law, the tax level and which tax sets it;
- one workbench row per tax the law levies: its range (where the "Law" column is), the rate,
  then − and +, which apply at once.

A button's tooltip says whether the step changes the tax level and how each group reacts. Shift
and right-click keep their meanings within the range (floor, ceiling). There is no draft, review
or politics section. "How the light tax code works" is one collapsed explanation.

## 9. Tests (task 5)

- `test_tax_code_rule.py` pins four options and the three trigger bodies, and checks that the
  gates, carrier and amendments use the full trigger.
- New: light bounds equal `MIGRATION` per law; the derived level is the highest rung; the relief
  statics and reaction values follow the formulas above; the clamp; and the probe harness's guard
  names the light option.
- The `/reload` check runs on a second server started from the worktree.
