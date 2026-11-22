# Formables play-test checklist

What the next play-test should look at in the mod's formable countries and the events that follow their formation
(`common/country_formation/te_formable_countries.txt`, `events/te_formable_formation_events.txt`). In-game checks do
not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and
adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through
with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Forming India fast.** A save from the decolonization era with India (`BHA`) formed is quickest; otherwise form it
  from the console as an Indian major power that holds the core.
- **Logs.** Read `debug.log`, not `error.log`.

## Operation Polo reaches only the holdout inside India's core (2026-11-20)

"The Holdout" (`formation_te.10`) used to be offered against any small Muslim-ruled neighbor of a formed India, and an
AI India annexed Persia whole with it, without a war. `te_operation_polo_target`
(`common/scripted_triggers/te_operation_polo_triggers.txt`) now also requires the target's capital to be in one of
India's core states and its rank to be Insignificant Power or Unrecognized Power. The state list and the rank gate are
tested offline (`test_operation_polo_target.py`); what the game alone shows is the capital test, `capital = {
state_region = s:STATE_X }`, which the mod already uses in its power bloc names.

| Check | Expect | If it fails |
|---|---|---|
| **The holdout still gets it.** As India, with an independent, Muslim-ruled, insignificant Hyderabad on the border, wait out the monthly pulse (or clear `operation_polo_cooldown`). | "The Holdout" names Hyderabad. | Nothing fires: the capital test is false for a capital in the core. Check `te_is_india_core_state` against the capital's state region in the console. |
| **Persia doesn't.** India borders Persia (Baluchistan taken), Persia independent and below Minor Power, no holdout in the core. | "The Holdout" never fires; Persia keeps its independence. | It fires naming Persia: the capital test passes outside the core. |
