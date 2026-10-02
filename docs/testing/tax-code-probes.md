# Tax code probes — minimal first run

**Goal: decide whether a small tax-code prototype is worth building.**
Aim for 10–15 minutes after loading; **stop at 15 minutes** and report what you reached.
One country, one disposable save, one pass. No special scenario collection or repeat runs.

## Setup (about 2 minutes)

Use the current mod containing the PR #585 harness, with no duplicate Workshop copy.
Restart in debug mode and load a **copy** of any quiet country save with employed wage earners.
Keep the original save untouched: **Zero carrier replaces the taxation law**.
Clear bench and Disarm do not restore it; reload the original when finished.

Pause, run `event te_debug_tax.1` in the console, and open
**Timeline Extended → Tax Probes**. Note whether the game loads and the tab opens.
If the tab fails, record that and use the console equivalents below.
If the game crashes or commands fail, stop and send the error; no troubleshooting marathon.

## 1. Can a scripted tax actually collect money? (about 5 minutes)

1. Click **Zero carrier** (`event te_debug_tax.3`). Advance about one game week and pause.
   In Budget, note the wage/income-tax rate and receipts. In a wage-earning pop's income
   tooltip, note its tax deduction. Rough numbers or screenshots are enough.
   If the effective wage rate is not zero, report the remaining rate and skip this check.
2. Click **Wage 0.05** (`event te_debug_tax.10`). Advance another week and inspect the
   same Budget channel and pop. Expected: a 5% wage rate, actual payer deductions,
   and wage-tax receipts above the zero baseline.
3. Click **Zero rates** (`event te_debug_tax.16`), advance another week, and check that
   the wage rate and that channel's receipts/deductions fall back toward baseline.

A rate label alone is not evidence of collection. Other taxes can remain on the pop;
look for the wage component or a clear change in its deduction. If it is hard to find,
write **unclear** and move on. Do not calculate national reconciliation, wait for a
perfectly stable economy, or chase small differences.

## 2. Can the ordinary Budget control be locked? (about 2 minutes)

While paused, confirm another native Budget tax level is normally selectable.
Click **Lock native UI** (`event te_debug_tax.57`) and try that Budget tax-level button:
it should not change the level. Click **Unlock native UI** (`event te_debug_tax.58`)
and try again: it should work. Use the ordinary Budget button, not a probe tax-level setter.

Report locked/unlocked behavior. No hunt through every menu, AI action, or bypass.
This checks only the Budget tax-level control.

## 3. Does the applied tax survive one reload? (remaining time)

Click **Zero carrier**, then **Wage 0.05** again. Check the 5% rate, save to a new
throwaway slot, and reload it once. Check that the rate is still 5%; advance about
one week and look for wage-tax receipts again. If loading is slow, skip this check
when the time cap is reached.

**Stop here.** Reload the untouched original save before normal play.
Paste the [short results form](tax-code-probe-results.md) into the follow-up PR or send it
to the developer. One sentence per check is fine. Attach a screenshot or relevant error
excerpt only where it helps explain a problem; no mandatory logs or save uploads.

## What happens next?

These observations can justify trying a narrow wage-tax prototype; they do not verify the
whole design. A failed or unclear check calls for one targeted follow-up or a fallback,
not a rerun of the entire suite. Untested features stay untested.

Customs, other tax channels, storage containers, scheduled bills, institutions, AI,
civil wars, exact accounting and performance are deferred until a concrete implementation
choice needs them. The [extended runbook](tax-code-probes-extended.md) and
[extended results form](tax-code-probe-results-extended.md) preserve the original reference,
including the command appendix and removal instructions. They are **not first-run
requirements or prerequisites for starting a prototype**; the developer should select
only a relevant subcase if needed.
