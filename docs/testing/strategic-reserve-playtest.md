# Strategic Reserve panel play-test checklist

What the next play-test should look at in the Strategic Reserve journal entry's panel and the Market panel's Reserve
tab. In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands
on the offline gate and adds what only the game can show here. Each PR adds its own section, newest last, and a fixed
item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The journal entry (needs Logistics and a Strategic Reserve Hub; the Establish a Strategic Reserve
  decision builds one), and the Market panel's Reserve tab on your own market.
- **Benches.** A reserve with several goods unlocked, one good full (keep storing until it fills), one on
  an automated policy, and one empty with a negative rate set.
- **Logs.** Read `debug.log`, not `error.log`.

## The GUI audit wave (2026-10-27)

The audit's findings SR-1 to SR-11 (`docs/audits/gui_audit/climate_reserve_market.md`). Offline,
`test_strategic_reserve_layout.py` and `test_strategic_reserve_lifecycle.py` hold the layout, the widths, the hovers'
keys and the scripted GUIs. No self-check line: every question below is about what the panel draws.

| Check | Expect | If it fails |
|---|---|---|
| **Rate stepper.** Read a collapsed row, then click + and − with the step at 100. | The rate between − and +, then the stop button; the figure changes on the click. | The rate figure blank: `st_res_row_<good>_rate_short` reads `JournalEntry.GetCountry`, which the Reserve tab provides through `GetPlayerJournalEntry`; check it on both hosts. |
| **Rate-button hovers.** Hover + on a good at rate 0 with step 100, then − and stop. | Each opens with "Rate Setting: 0 → 100 a week" (or the clamped figure), then what stops it, if anything does. | No before/after line: the base effects' `custom_tooltip` did not reach `ExecuteTooltip`. A wrong after-figure: compare with `st_res_<good>_rate_after_up` / `_down` at the cap and at full or empty storage. |
| **Per-cell hovers.** Hover the Stock bar, the status icon, the policy icon and the rate figure; expand the row and hover Rate Setting and Decay. | Stored and capacity with what the marker means; the status word and its reason; the policy and what it is doing; the rate's definition; the active rate; the decay breakdown. Nothing pops over the row as a whole. | A hover missing: the blockoverride name in that row instance; the eight rows are generated from the grain row. |
| **Selected policy and preset.** Open a good's Policy Settings with Stabilize Prices and the Standard preset in force. | Stabilize and Standard drawn in vanilla's selected-tab look with their label, the other choices as buttons. Click another policy: the look moves. | Every choice a button, the one in force grayed: `scope:op` did not reach `st_res_policy_<good>_sgui`'s `is_shown` (fail-open, `gui_modding_guide.md` gotcha #22); nothing is lost. No choice drawn at all for one op: both visibilities false, which would mean `IsShown` erred; revert to the plain button. |
| **Overview cells.** Read the four overview boxes with the bench above. | Hub with its word and "Cap N/wk"; Blocked with "1 empty" in red (or "N full" in orange, or "None" in green) and "and N full" when both; Purchases and Sales Income as money a week. Text at 16, nothing elided. | A cell's text cut short: shorten the key or check the font template. |
| **Blocked hover.** Hover Blocked. | One line per good that is full, or empty with a release set, then the note on Silos. | No lines with a count above zero: `st_res_ov_held_sgui`'s `custom_tooltip` branches did not print through `ExecuteTooltip`. |
| **Purchases estimate.** Buy one good at a set rate for two weeks; compare Purchases with the Budget panel's Goods for Government Buildings line for the hub. | Close to the budget's figure (the hub pays at market prices through its production method). | Far off: `st_res_<good>_purchase_cost` reads the wrong rate; say "estimate" louder in the hover, or drop the cell. |
| **Releasing.** Set a negative rate on a stocked good. | The status hover and the row say "Releasing". | "Withdrawing" left in a key: search the loc. |
| **Type sizes.** Read the rows, the Policy Settings and the step line at 1080p. | Rows, buttons and steppers at 17, subheadings at 20; "Release High" and "Conservative" fit their buttons. | Note the control and its text; the width budget is wrong for that face. |
