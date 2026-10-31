# Wonder Buildings

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## Wonder Buildings (Construction Site Pattern)

> **Full design document:** `docs/vanilla/wonder_buildings_reference.md`

The seven **megaprojects** use a two-phase construction pattern: a buildable construction site becomes the completed building through a scripted effect. (The ordinary wonders in `common/buildings/wonders.txt` are built through the normal construction queue and are not covered here.) All seven are era-12 technologies; their sites and buildings live in `common/buildings/extra_buildings.txt`.

| Megaproject | Tech | Max level | Completed building does |
|---|---|---|---|
| Space Elevator | `space_elevator` | 20 | 1M `launch_capacity` per level, `country_space_race_progress_add` |
| Orbital Solar Collector | `space_based_solar_power` | 10 | an orbital hub: each level opens 3 `building_solar_receiver` slots (`country_solar_receiver_max_level_add`); the ground receivers produce the electricity |
| Orbital Battlestation | `orbital_weapon_platforms` | 5 | country-wide unit offense/defense/morale and nuclear-defence chance; no goods output |
| Antimatter Containment Facility | `antimatter_production` | 10 | each level opens 5 slots (`country_antimatter_facility_max_level_add`) for `building_antimatter_engine` and `building_antimatter_warhead_plant` |
| Mind Upload Nexus | `mind_backups` | 5 | digital assets, services, tourism and fine art output, research speed; under the Demographics rule's Full setting both follow the uploaded minds it hosts (§ Demographics, Uploaded minds) |
| Nanofabrication Center | `molecular_assemblers` | 10 | `advanced_materials` output, lower space race risk |
| Consciousness Network | `telepathic_communities` | 10 | state infrastructure, tax capacity and institution impact, bureaucracy; a mode group picks Open (SoL, innovation, influence) or Social Control (authority, less turmoil; unlocked by the laws that disallow Open) |

- **Construction effect:** `generic_wonder_construction_base = { WONDER = <name> MAX_LEVEL = <n> }` in `common/scripted_effects/extra_effects.txt`, called through one named wrapper per megaproject (`space_elevator_construction`, …). Each megaproject's `<name>_on_action` runs it from `on_monthly_pulse_state` (`common/on_actions/extra_on_actions.txt`). On completion it removes the site and creates the building at level 1, or raises it one level up to the cap; a site can't be placed once the building is at its cap.
- **Construction progress:** each month, `building_annual_<name>_progress / 12`, and nothing while the site has a goods shortage. The PM puts that modifier in `workforce_scaled`, so it already scales with staffing and progress is linear in occupancy; until 2026-10-01 the tick multiplied by `occupancy` again, so a half-staffed site ran at a quarter speed. The site's `<name>_progress` modifier mirrors the state's `<name>_progress_var` (`multiplier = root.var:…` from the state pulse). Speed PMs set the annual progress: paused 0, slow 0.25, medium 0.5, fast 1.0 (about 4 / 2 / 1 years at full occupancy).
- **Custom modifier types:** `building_annual_*_progress` and `building_total_*_progress` (script_only) in `megastructure_progress_modifier_types.txt`.
