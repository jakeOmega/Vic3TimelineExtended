# AI-managed flat staff: play-test

Prototype: `pm_ai_managed_fab` hires a flat crew of 1,000 engineers per building instead of 10 a level, so a building's level is no longer limited by the population that can staff it (`docs/superpowers/archive/specs/2026-10-16-ai-managed-flat-staff-design.md`).

The fab buildings are the Wired and Wireless Telecommunications, Consumer Appliance, Electronic Components and Semiconductor, and Robotics industries.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … ai_managed_flat_staff` | once a game: the first yearly pulse of a country with a fab building of level 5 or more on AI Managed Fab (a random one if it has several) | the building's engineer slots read about 1,000 at any level: an `unscaled` employment add counts once per building | `engineers` about 1,000 × `level`: `unscaled` employment is read per level, and the crew grows with the building. `engineers` 0: it isn't summed, or the script read failed; confirm in the building panel before taking the fallback. A building switched to the method within a day of its owner's yearly pulse can still read its old base sum, which mimics the per-level case (odds about 1 in 365) | in `pm_ai_managed_fab` (`common/production_methods/extra_pms.txt`) restore `building_employment_engineers_add = -1990` in `level_scaled` and drop the `unscaled` block (10 engineers a level, as before) |
| `TE_SELF_CHECK … ai_managed_flat_output` | once a game: the first yearly pulse of a country with a fab building of level 5 or more on AI Managed Fab that is at least 90% staffed | `robotics_per_level` between 2 and 20: the method's robotics input (4 a level, workforce-scaled, × throughput) follows every level with a flat crew | `robotics_per_level` under 2: workforce-scaled goods follow one level's worth, or none, so the building produces as if it were small. Over 20: goods scale with something besides level × staffed share, such as the headcount. No line at all within a few years of the staff line means no such building ever filled its crew | the same |

## In the building panel

1. Research Artificial General Intelligence (era 12). Put a Robotics Industry of level 5 or more on AI Managed Fab.
2. A month later, its employment shows about 1,000 engineers and no other professions. Before this change it showed 10 engineers a level (50 at level 5).
3. Its output is its base method's output per level × its level (× throughput), as the output tooltip lists. Check this most of all. Don't compare it with a building that isn't AI-managed: in era 12 those are often short of workers.
4. The rollout gives the same crew to Arms Industries, Chemical Plants, Explosives Factories, the Synthetics Plants, and Power and Renewable Energy Plants. Spot-check one of them: about 1,000 engineers and no one else, at any level.
5. The split buildings show one AI-managed option each, whatever their base method: an Artillery Foundry, a Motor Industry on Gas Turbine Engines, a Munition Plant on Explosive Shells, a Fusion Plant and a Hydro Plant. Each employs the crew alone.
6. The crew fills and stays (owner, 2026-10-30). All fourteen flat-crew methods carry `building_job_attractiveness_mult = 5` in `unscaled`, the Grid Transfer Station's bonus (`power_grid_pms.txt`), because the game hires a group of 1,000 slowly and unevenly. A month or two after a building switches, its engineers should read at or near 1,000, and a year on, hardly any building should sit far below it. If many do, look for a state short of engineers (qualifications, which attractiveness doesn't fix), then raise the value. If other engineer employers (universities, offices) lose staff to the crews, lower it. `test_ai_managed_flat_staff.py` fails a flat-crew method that lacks the line.
