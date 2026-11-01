# Local Climate play-test checklist

What the next play-test should look at in Local Climate (`docs/systems/mod_systems/local_climate.md`; spec
`docs/superpowers/specs/2026-11-01-local-climate-design.md`). In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here.
Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The state panel's status grid: the Local Climate tile sits after Migration Crowding (or where
  Migration Crowding would be) on every state.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `te_state_climate`, `local_climate` and `TE_CLIMATE_`.

## Readings (phase 1, 2026-11-01)

| Check | Expect | If it fails |
|---|---|---|
| The tile on an ordinary state (Georgia, the Home Counties) | Five rows: Summer and Winter in °C, Humidity, Water and Malaria as words; Georgia reads 28°C, Sultry, 8°C, Ample, Endemic | A raw key or `0°C`: the loc's `State.MakeScope.ScriptValue` read failed in the tile; check `debug.log` |
| The tile on a split region (Hamburg's or Bremen's piece of Elbe) | The same readings as Hanover's piece | The values aren't keyed on `state_region` |
| The words' nested `SelectLocalization` | Each class shows its own word (find a Dry, a Moderate and a Humid state; a Limited and a Scarce one; a Seasonal one) | Every state shows the same word: the nesting reads one test only |
| No row elides with "..." | "Humidity", "Seasonal" and "Moderate" fit their columns | Widen `te_state_climate_row`'s columns |
| Hovers | Each row's hover explains its reading; the tile's hover names Local Climate | |
| Fiji, Tonga, Namaqualand; Zambezi, Botswana | No malaria trait on the first three (the tile reads Malaria: None); the mild Malaria trait, not Severe, on the other two (Seasonal) | The deployed `12_indonesia.txt` is stale, or a later-loaded mod overrides it |
