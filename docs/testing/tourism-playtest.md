# Tourism play-test checklist

What the next play-test should look at in the tourism card. In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here.
Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** Open a state's panel; the tourism card sits above the status grid. Its Throughput column lists the
  sources, and the footer's "All modifiers" line shows what the engine applied (up to a month behind the sources).
- **Logs.** Read `debug.log`, not `error.log`.

## Excess infrastructure replaces Ports and Transit

The Ports row (per Port level) and the Transit row (per Railway and Highway level) became one Excess Infrastructure
row: `0.72 × E / (E + 3000)`, where E is the state's infrastructure less its usage, floored at 0
(`tourism_throughput_from_infrastructure` in `common/script_values/tourism.txt`). Nothing in the offline gate can tell
whether the 3000 is right, because the repo holds no late-game save: it was set from the old tiers by estimating how much
infrastructure a state with about a hundred levels each of Railway and Highway has to spare (the old bonus there was
+40% with a Port of the same size).

| Check | Expect | If it fails |
|---|---|---|
| **Scale.** In a developed late-game state, read the row's value beside the state's infrastructure and usage (the vanilla state panel shows both). | The row equals `0.72 × spare / (spare + 3000)`: about +18% at 1,000 spare, +36% at 3,000, +54% at 9,000. The bar is half full at 3,000. | A wrong figure means the script value is not reading the state's balance: check the scope the monthly pulse evaluates it in. |
| **Calibration.** Compare developed states across a game: a core industrial state, a rail-heavy agricultural one, a tourist coast. | Most developed states land between about +10% and +50%. A state that overbuilt rail reads high; a crowded industrial one reads near 0. | Most states under about 10% or over about 60%: move the half-point. It is in `tourism_throughput_from_infrastructure` and `tourism_fill_infrastructure_pct`; the same figures are in `te_state_tourism_infrastructure_tt`, `docs/player_guide/08-states.md` and `docs/systems/mod_systems.md`. |
| **Negative balance.** Find a state whose usage exceeds its infrastructure (market access under 100%). | The row reads +0%, not a negative figure. | A negative figure means the floor is missing from `tourism_excess_infrastructure`. |
| **Coastal states.** A coastal state with a large Port and little rail. | It no longer gets a bonus for the Port as such; a Port adds only the few points of infrastructure it supplies. This is intended. | Tourist coasts that read badly low are a calibration question for the owner, not a bug. |
| **Refresh.** Build or demolish a Railway, then wait for the next month. | The row and the "All modifiers" throughput line move together after the monthly pulse. | A row that moves while "All modifiers" does not means `tourism_on_action` did not re-apply the modifier. |
| **Display.** Hover the row's label and its bar. | The label reads "Excess Infrastructure"; the hover text gives the three sample points and "Maximum: +72% (approached, never reached)". The concept's link opens its description. | A raw key (`concept_tourism_infrastructure`, `te_state_tourism_infrastructure_tt`) means the loc did not load. |
