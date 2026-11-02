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

## Comfort (phase 2, 2026-11-01)

| Check | Expect | If it fails |
|---|---|---|
| The modifier's size | A state's migration attraction breakdown shows "Local Climate" at minus the tile's Comfort figure (Georgia about −14.6 in 1836, Yakutsk about −32) | −1: the multiplier was applied as ×1, not read from `var:te_climate_penalty_applied`, so `add_modifier`'s multiplier didn't resolve against the state |
| First application | Within the first month of a new game every state has the Comfort figure, not Pending, and a state with a cost carries the modifier; an old save gets them within a month of loading | The monthly on-action's `trigger` isn't read, or `te_update_local_climate_modifier` fails at state scope |
| One copy | A year on, the breakdown shows one Local Climate line, not two | The remove before the add misses the old copy |
| Hidden from the rows | "Local Climate" isn't among the state panel's modifier rows, in the full or the condensed view; the condensed box still fades when the state carries nothing else | The name filter compares against markup: the modifier's loc must stay plain "Local Climate" |
| Comfort rows | London and Paris read None; Georgia a red figure; a state in the first month reads Pending | The `And(...)` visibility chains |
| Hovers | Summer's hover gives today's normal and a negative shift in 1836 (about −1.2°C at Savannah), heat before and after relief, and the relief as a percentage; Comfort's hover splits the total into heat, cold, dry land and malaria | A `0` relief with the technology held: `modifier:state_climate_heat_relief_add` doesn't reach the state from a technology |
| Relief arrives | After Personal Appliances, Georgia's heat relief reads 35% more than before, and its Comfort falls at the next yearly refresh | The INJECT on a vanilla technology didn't merge (`te_local_climate_tech_injections.txt`) |
| End of the game | A country holding every carrier (era 13, Programmable Matter) shows Comfort None in every state | A relief sums to 0.99999, not 1, in fixed point |
| Warming | At 1.1 °C of world warming the tile's Summer and Winter read the record's normals (Savannah 28°C, Yakutsk −38°C winter); past it they read warmer, most at high latitude | `te_climate_normals_warming`, or `temperature_anomaly_display` read from state scope |
| The define | No `defines.cpp:167 … MASS_MIGRATION_TARGET_MIN_ARABLE_LAND not valid` line at load (0 logged one, 2026-11-01). `TE_LOCAL_CLIMATE yearly_targets_summed=N under_10_arable=M years=Y` in debug.log in 1836 and each decade after, with numbers (seen 2026-11-01, so the accessors work); `under_10_arable` above 0 in some decade (a city-state or a small partial state picked as a mass migration target) | Blanks: the global variable accessors; always 0: the define isn't read, or small states never win on attraction |
| The concept | The Migration Target concept's text says nothing about arable land | The `replace/` override isn't loaded |
| Internal migration in a hot, poor market | India's or Brazil's internal migration to about 1880, against a run with comfort off: migrants still move from the poorer states to the richer, at a volume near the comfort-off run's | Attraction floors at 0, so a penalty every state shares can pin the poorer states there and erase the gaps between them; pops don't move for a gap under 5 points, so internal migration stalls. Fallback: a percentage cut (`state_migration_pull_mult`) in place of points, which scales every state alike, or a lower cap |
| Observer run to 1930 | The US South's net migration below the North's; no desert state (Sahara, Nejd, Arizona) a mass migration target before era 4 | The calibration's heat or dry weights are too low |
| Destination shares to 1914 | Against an observer run without comfort (the formula's constants at 0): fewer mass migrations to the tropics and Siberia, more to temperate coasts | |

## Heat v2 (2026-11-01)

Heat from each region's hottest days, a steepening curve, and the cost in percent (spec § 11). It supersedes phase 2's
figures above: Georgia's Comfort is now about −28%, not −14.6 points.

| Check | Expect | If it fails |
|---|---|---|
| The modifier's size | The migration attraction breakdown shows "Local Climate" as a percentage equal to the tile's Comfort (Georgia about −28% in 1836, Yakutsk about −65%, Oman −80%) | −1%: the multiplier didn't resolve against the state, so the modifier applied once; a points figure: the old static modifier is still deployed |
| Hot days row | Georgia reads 35 or 36°C in 1836; its hover gives the record's 37°C, a −1.1°C shift and a heat stress reading near 29.3 | A raw key or `0°C`: the renamed loc keys (`te_state_climate_hot_day_*`) didn't deploy |
| The owner's case | Hawaii's Comfort is about −1%, below Norrland's (about −14%) and Paris's (about −3%) | The heat index column or the curve |
| Small costs | London reads None; no Comfort row reads −0% (a hover may list a term at −0%) | The 0.5 gates in the tile and the refresh disagree |
| Old save | A save from before heat v2 shows its old points as a percentage (Georgia −15%, Hawaii −8%) until the state's yearly refresh, then the new figure (Georgia −28%, Hawaii −1%) | The variable is not rewritten at the yearly pulse |
| Internal migration in a hot, poor market | India's or Brazil's internal migration to about 1880, against a run with comfort off: migrants still move from the poorer states to the richer, at a volume near the comfort-off run's. The percentage cut keeps the gaps in proportion, so this should now pass where phase 2's points could stall it | A share every state pays still pinning poor states at 0: lower the heat curve or the cap |
| Warming and the cold north | At +3 °C, Yakutsk's Comfort falls (cold eases faster than its hot days start to cost) and Georgia's rises | Winter amplification not applied (`te_climate_winter_warming`) |

## Winter's mildness (2026-11-01)

Winters measured against London's, a small bonus for milder ones, and Winter Relief (spec § 12). It supersedes the
heat v2 figures above where they differ: Georgia is now about −25%, Hawaii about +6%.

| Check | Expect | If it fails |
|---|---|---|
| The bonus | Madeira's tile reads Comfort +7% in green, and its migration attraction breakdown shows "Local Climate +7%"; Hawaii about +6%, Cape Colony +5% | No line: `local_climate_amenity` wasn't added (`te_climate_bonus_applied` not set); "−7%": the cost modifier applied a negative penalty |
| London | Comfort reads None; Glasgow about −1% (red); Paris about −4% | The neutral point (`te_climate_winter_neutral`) |
| Hidden | Neither "Local Climate" modifier appears among the state panel's modifier rows | `local_climate_amenity` missing from the `TimedModifier.GetName` filters |
| Winter hover | Madeira's Winter hover: a +7% draw before relief, Winter Relief 0%, +7% left; Massachusetts' a −4% draw and a frost cost | `te_climate_winter_draw` signs |
| Winter Relief | Water-tube Boiler's tooltip lists Winter Relief +10%; after it, Madeira's bonus and Massachusetts' winter cost both shrink a tenth at the next yearly refresh | The INJECT line in `te_local_climate_tech_injections.txt` |
| The Sun Belt | In an observer run to era 7, the US South's migration attraction overtakes New England's | Heat relief or the winter term's weights |
| A save from heat v2 | Every state refreshes within a month of loading (the first application keys on `te_climate_bonus_applied`), so Madeira shows its bonus by then | The monthly on-action's trigger |
| Signed hover figures | Madeira's Winter hover shows its draw as a green +7%, Massachusetts' as a red −4%; London's draw of −0.02 may print −0% or +0% | `|+=0` shows a sign but no color: wrap the figures in `#G`/`#R` by sign |
