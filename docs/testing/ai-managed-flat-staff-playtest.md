# AI-managed flat staff: play-test

Prototype: `pm_ai_managed_fab` hires a flat crew of 1,000 engineers per building instead of 10 a level (`docs/superpowers/specs/2026-10-16-ai-managed-flat-staff-design.md`).

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … ai_managed_flat_staff` | once a game: the first yearly pulse of a country with a fab building (Wired or Wireless Telecommunications, Consumer Appliance, Electronic Components and Semiconductor, or Robotics industry) of level 5 or more on AI Managed Fab | the building's engineer slots read about 1,000 at any level: an `unscaled` employment add counts once per building | `engineers` about 1,000 × `level`: `unscaled` employment is read per level, and the crew grows with the building. `engineers` 0: it isn't summed, and the building can't hire | in `pm_ai_managed_fab` (`common/production_methods/extra_pms.txt`) restore `building_employment_engineers_add = -1990` in `level_scaled` and drop the `unscaled` block (10 engineers a level, as before) |

The modifier read can't show whether the slots are actually hired. Look once in the panel as well.

## In the building panel

1. Research Artificial General Intelligence (era 12). Put a Robotics Industry of level 5 or more on AI Managed Fab.
2. A month later, its employment shows about 1,000 engineers and no other professions. Before this change it showed 10 engineers a level (50 at level 5).
3. Its output matches a same-level building on the same base method without AI management. Check this most of all: occupancy near 100% with full per-level output means `workforce_scaled` goods follow the staffed share of a flat crew. Output near one level's worth means they don't, and the fallback above applies.
