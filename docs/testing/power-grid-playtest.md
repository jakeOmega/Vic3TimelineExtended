# Power grids: play-test checklist

What the next play-test should look at in the power grid: the Grid Transfer Station, the Grid Power good and the
monthly balancing (`docs/systems/mod_systems.md` § Power Grids). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Setup.** Research Electrical Capacitors (era 4) and build Power Plants in one state and none in a neighbour, so the
  two have Electricity at very different prices. Build a station in each, the second bordering the first.
- **Where to look.** A station's building panel (its goods, its modifiers Grid Upload / Grid Download, its subsidy),
  the state panel's Electricity price, and the market panel's Grid Power row.
- **Logs.** Read `debug.log`, not `error.log`. Search for `TE_SELF_CHECK` and `grid`.

## Self-checks

| Line | What it means | Fallback if BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK grid_conservation` | A country's stations uploaded within 10% of what they downloaded, a week after the balancing ordered both sides to move 100 or more. | — |
| `TE_SELF_CHECK BROKEN grid_conservation` | Uploads and downloads more than 10% apart: the staffing correction (`te_grid_station_factor_value`) isn't holding, or something else trades Grid Power. | Compare each station's ordered quantity (`te_grid_command`) with what its panel shows. If the factor is stuck at its 0.2 or 2 clamp, widen it or drop the correction and accept per-station staffing as capacity. |
| `TE_SELF_CHECK BROKEN grid_readback` | Both totals read 0 while two stations were ordered to move 100 or more: `sg:grid_power` reports nothing in a station's state. | Read the station's flows from its own orders instead (`te_grid_command` × factor 1) in `te_grid_local_production_value` / `te_grid_local_consumption_value`, and drop the factor. |

## Phase 1: the Grid Transfer Station and the balancing (2026-10-22)

| Check | Expect | If it fails |
|---|---|---|
| **Placement.** With no station in a market area, open the build menu in a state there; then try a state that doesn't border the first station. | The first station can go in any state of that market area. The second can go only next to one. The tooltip names the rule. | Every state blocked: `any_neighbouring_state` or `is_in_same_market_area = ROOT` isn't read as expected in `possible`. Every state allowed, a second station included: ROOT isn't the state in a building's `possible` (no vanilla or mod building uses ROOT there); compare with `PREV` or restate the checks from the owner. A non-adjacent second station allowed: the queued first station isn't counted by `has_building` (expected while it is only queued; check again once it is built). |
| **Overseas.** Own states in two market areas (a colony across the sea). | Each market area takes its own first station, and the two grids never share power. | — |
| **One per state.** Try to expand a station. | Max level 1. In a state region split between two owners, both can build one. | Expansion allowed: the `base_values` cap isn't applied. A split region blocked for the second owner: `ignore_stateregion_max_level` isn't honoured. |
| **Subsidy.** Open a station's panel under any economic law. | Subsidized, and it can't be unsubsidized. Its losses show in the budget's subsidies line. | Not subsidized: the require-subsidies bool doesn't work on this building. Use the pulse fallback, `set_subsidized = yes` on each station (`te_company_effects.txt` pattern). |
| **Direction.** A month after both stations are staffed. | The surplus state's station shows Grid Upload: it buys Electricity and makes Grid Power. The short state's shows Grid Download: it buys Grid Power and makes Electricity. The two Electricity prices move toward each other. | No goods at all: the `_mult` modifiers don't scale the method's 1-unit lines (check `debug.log` for `Unknown modifier type: goods_*_grid_power_*`). Both directions at once: a `-1` modifier isn't zeroing its lines. |
| **Grid Power price.** Watch the market's Grid Power row for a few months. | Near its base price of 30, with supply about equal to demand. | Far from base: a grid's uploads and downloads differ; see the conservation self-check. |
| **No stacking.** Fast-forward several months. | Each station carries one Grid Upload and one Grid Download modifier, never more. | Copies piling up: `remove_modifier` isn't clearing the old copy. |
| **Damping.** Watch a station's flow over several months while factories hire. | The flow settles; it doesn't swing from upload to download month to month. | Oscillation: lower the 0.7 step in `te_grid_flow_value`. |
| **New station.** Build a third station while the first two run. | It stays idle until a quarter staffed, then joins without the other two jumping. | — |
| **Captured station.** Lose a station's state in a war. | The new owner's next monthly pulse takes it over: idle, or in that owner's own grid. | — |
| **AI.** An observer run to the 1920s. | AI countries with Electrical Capacitors build some stations, mostly in states where Electricity is dear or cheap. | None built: `te_grid_station_ai_value` is too low, or the AI won't build private infrastructure with government construction. Consider a spawn decision (the Strategic Reserve and Space Program pattern). |
| **Display.** Hover the station, its method and its modifiers; open the Grid Power good. | Names and descriptions read as text. The texticon shows the Electricity icon (a placeholder until Grid Power has its own art). | A raw key: missing loc. |
