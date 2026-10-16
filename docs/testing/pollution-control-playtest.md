# Pollution-control play-test checklist

What the next play-test should look at in the seven pollution-control production method groups (`pmg_tailings_wastewater_management` to
`pmg_emissions_control`, `common/production_method_groups/extra_pm_groups.txt`). In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR adds its own
section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Setup.** A late-game country with Pollution Control researched and several Glassworks, one per combination in the checks below. Save
  before establishing the Ministry of the Environment so each check can start from the same state.
- **Where to look.** The building's production method panel (the Fume Ventilation group), and the state's pollution breakdown.
- **Logs.** Read `debug.log`, not `error.log`.

## Glassworks: Fume-Free Process

Under the ministry, a Glassworks on Forest Glass or Bioplastics with Manual Glassblowing or Programmable Plastics had no allowed Fume
Ventilation method. No Fume Ventilation needs `law_no_ministry_of_the_environment`, and both tiers unlock only beside a polluting method, so
that no combination goes below zero pollution. Bioplastics with Mass-Produced Plastics (5 pollution) had none either, because Fume
Extraction's unlock list left that automation method out.

Fume Extraction now also unlocks beside Mass-Produced Plastics. A new Fume-Free Process (no cut, no cost, hidden while unavailable) is allowed
under the ministry beside Forest Glass or Bioplastics. It carries `replacement_if_valid = pm_glassworks_fume_extraction`, so a building that
pollutes (Forest Glass or Bioplastics beside Automatic Bottle Blowers or Mass-Produced Plastics) should move on to Fume Extraction.
`test_pollution_control_groups.py` checks every combination offline. It can't see which method the engine picks when the current one stops
being allowed, nor whether `replacement_if_valid` fires for a target gated by another group's method (the mine maintenance swap relies on
the same and is also unverified, `docs/systems/mod_systems.md`).

| Check | Expect | If it fails |
|---|---|---|
| **Ministry on a clean building.** Forest Glass + Manual Glassblowing on No Fume Ventilation; establish the ministry. Repeat with Bioplastics + Programmable Plastics. | The group moves to Fume-Free Process, the only allowed method. State pollution is unchanged. | Still on No Fume Ventilation, or no method shown: the engine did not apply the fallback. Record what the panel and `debug.log` show. |
| **Ministry on a polluting building.** Leaded Glass + Manual Glassblowing, and Forest Glass + Automatic Bottle Blowers, both on No Fume Ventilation; establish the ministry. | Both move to Fume Extraction, never to Fume-Free Process. | Forest Glass + Automatic Bottle Blowers resting on Fume-Free Process: `replacement_if_valid` did not fire. See the swap check's fallback. |
| **Swap into pollution.** Under the ministry, switch a Fume-Free Process building from Manual Glassblowing to Automatic Bottle Blowers, and another from Programmable Plastics to Mass-Produced Plastics. | Fume Ventilation moves to Fume Extraction by itself; the building's net pollution stays at 0 (+5 −5 per level). Fume-Free Process can't be picked back while the polluting method runs. | It stays on Fume-Free Process: the swap does not fire for a target gated by another group's method. The building then pollutes 5 per level under the ministry; the guide's "at least the basic method" fails for these four combinations. Tell the owner before changing anything. |
| **Swap out of pollution.** Under the ministry, switch a Leaded Glass + Manual Glassblowing building on Fume Extraction to Forest Glass. | Fume Ventilation moves to Fume-Free Process (Fume Extraction's unlock is gone). | It stays on Fume Extraction: the building then reads −5 pollution per level. Record it; the owner-confirmed carbon-capture check (`docs/testing/carbon_capture_probe/README.md`) says the engine moves off a method whose unlock goes. |
| **AI.** An observer run with AI countries holding the ministry, a few years. Watch AI Glassworks on Forest Glass or Bioplastics. | No repeated switching between Fume-Free Process and Fume Extraction (each switch applies `pm_retooling`). | Repeated switches mean the AI can pick a method whose replacement is allowed. Fallback: drop `replacement_if_valid` from `pm_glassworks_fume_free_process` and accept the 5-per-level gap on those combinations. |
| **Display.** Hover Fume-Free Process; look at the group before the ministry and on a polluting building under it. | The name and its description ("None of this Glassworks' production methods give off fumes…"). The method is hidden before the ministry and while a polluting method runs. | A raw key (`pm_glassworks_fume_free_process`) means the loc did not load. |
| **Repeal.** Repeal the ministry with a building on Fume-Free Process. | It moves back to No Fume Ventilation. | It stays on Fume-Free Process: harmless (both do nothing), but record it. |
