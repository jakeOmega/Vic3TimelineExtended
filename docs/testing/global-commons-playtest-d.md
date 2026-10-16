# Global Commons play-test list, part D: orbital debris and the anti-satellite strike

Spec: `docs/superpowers/specs/2026-10-16-global-commons-design.md` § 6.1–6.4 and § 7's
event `.31`. Systems doc: `docs/systems/mod_systems.md` → Space Race → *Orbital debris*.
In-game checks don't gate the merge (CLAUDE.md § "In-game checks"); the play-test before a
release works through this list. The console harness is `event te_debug_orbital_debris.1`:
it sets the pools to each tier, runs the month's step at once, fires a ribbon strike and puts
the Space Program on its best removal method, and every option writes a `TE_DEBRIS` line to
`debug.log`.

## Self-checks (every game, space race rule on)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … debris_removal` | once a game: the first global monthly pulse at which some country's Space Program runs a debris removal method at half staff or more | that country's `country_orbital_debris_removal_add` reads above 0 (`removal` > 0): a secondary method group's workforce-scaled country modifier reaches the country, and the registered type is read | `removal` 0: no country's removal counts, so debris is never cleared by anyone | compute the removal in script: `te_debris_removal_country` reads the Space Program's active method (`has_active_production_method`) times its `occupancy` times the method's rate (mirror values beside `te_debris_units_*`), and the UN's Delivery term reads that value in place of the modifier |

No line at all means no Space Program has yet run a removal method at half staff: take the
decision Begin Orbital Debris Removal and wait a month.

## Play-test items

1. **The Mission Control row.** On any running milestone's panel, in the journal and on the
   Timeline Extended window's Space Race tab: "Orbital Debris: N (tier)" below the Estimate.
   Hover: the two pools, the costs at this level, the ribbon line from Hazardous, the cascade
   line from Kessler Cascade, and the cleanup line (the world's removal, how many countries,
   the largest cleaner's name, ours), or the "Nobody is removing debris" line. Check the
   largest cleaner's name renders (it reads the global `te_debris_top_cleaner` through
   `GetGlobalVariable(...).GetCountry.GetName`, a form proven in loc but not in this row), and
   that the row never pushes the panel wider. In solar colonization's passive mode the row
   is the first thing in Mission Control: check the section doesn't look cramped.
2. **The penalty.** With the console at Hazardous (60): a country with a Space Program shows
   Orbital Debris in its modifiers at multiplier 60 (setback risk +60%, pace −18%), the
   panel's risk and pace move with it, and an Extraplanetary Base, Space Elevator, Orbital
   Battlestation and Solar Receiver each show −12% throughput. The Orbital Solar Collector
   itself must show no throughput change (deliberate: see mod_systems.md). Check the
   Battlestation's unit bonuses fall with its throughput (the mod's docs say workforce-scaled
   country modifiers scale with throughput; if they don't, the Battlestation's penalty only
   saves upkeep, and should move to a unit modifier instead). A country with none of those
   buildings has no Orbital Debris modifier.
3. **A ribbon strike** (play-test list of the spec). Own a Space Elevator, console to
   Hazardous, option g: the event Ribbon Strike, its picture, both option tooltips stating the
   −50% for 6 or 2 months, the repair option showing its treasury cost. After either option
   the elevator building shows Ribbon Strike, and option g again does nothing until it ends.
4. **A Kessler cascade cleared by Fusion Sweepers** (play-test list of the spec). Console to
   Kessler Cascade (90), research Muon-Catalyzed Fusion Reactors, own a Space Elevator of ten
   levels, take Begin Orbital Debris Removal: the Space Program switches to Fusion Sweepers,
   the hover shows our removal near 1.0 a month, the index falls under 75 within about
   15 months and to near the background level within about 8 years, and Orbital Cleanup gives
   about +10% prestige. With Active Debris Removal alone the index must stay at 75 or above.
5. **The ceiling.** Console to Kessler Cascade, then strike several times (or option c again):
   the index stops at 100, and the high pool keeps its share (the low pool gives way).
6. **The anti-satellite strike.** At war with a country that has a Space Program: the action
   Anti-Satellite Strike appears in its diplomatic actions (and in the lens bar, with the
   placeholder icon), greyed with each failing requirement's line until all hold. The
   confirmation box lists the network penalty (and its six-month and half-strength cases),
   the infamy, the case strength, the relations and the debris. After the strike: the target
   holds Orbital Network Disrupted for a year (half strength with a Battlestation, six months
   on the Mars Mission or higher), we gain 5 infamy, Our Record on the UN tab shows
   Anti-satellite strikes 15 (with a UN), every other country in orbit likes us 30 less, the
   index rises by 12, both notifications read correctly (ours and the third party's), and the
   action is greyed against that target for 12 months for every country.
7. **The AI and the strike.** In an observer run with a late war between space powers: an AI
   strikes only an enemy with more in orbit than itself, rarely, and almost never once the
   index is 50 or more unless it is losing. An AI should never strike a country with no
   Space Program or orbital megaproject (the action's `possible` forbids it).
8. **The AI and removal (watch item).** In the same run, once the index reaches 25: AI orbit
   users take Begin Orbital Debris Removal. Watch whether the AI's own production-method
   choice then holds the method, flips it back to No Debris Removal (`ai_selection =
   most_productive` with cost-only methods is unobserved), or turns removal on by itself at
   a low index. Either flip-back or always-on is survivable; flip-back with re-taking every
   month is the one to fix (a `cooldown` on the decision, or `ai_value` on the methods).
9. **Event `.31`** (The Kessler Threshold) at Cluttered or above, for a programme outside
   Orbital Flight: the description names the tier, and its options add progress to every
   running milestone.
10. **The game rule off.** Space Race disabled: no Orbital Debris row (no panels), no strike
    action, no decision, and the Space Program's Debris Removal methods other than None are
    unavailable (the rule's `disable_pm_*` flags; the mod's first use of them).
11. **A revolution.** A country holding Orbital Debris and Orbital Cleanup loses a civil war
    to its rebels: the winner has both back after its next monthly pulse, and a struck
    country's 12-month cooldown carries over.

## Placeholder art

| Where | Now | Final art (icon-pipeline subject) | Proposed path |
|---|---|---|---|
| `te_asat_strike_action`'s `texture` | `diplomatic_action_icons/covert_space_espionage_action.dds` | an interceptor missile streaking up toward a small satellite that is breaking into fragments | `gfx/interface/icons/diplomatic_action_icons/te_asat_strike_action.dds` |
| the lens bar | `lens_toolbar_icons/te_asat_strike_action.dds`, a byte copy of the same placeholder | the same picture (the pipeline's lens copy) | unchanged |
| `pm_debris_active_removal` | `cat_star_purple_p1.dds` | a small servicer spacecraft grappling a dead satellite with a robotic arm | `gfx/interface/icons/production_method_icons/debris_active_removal.dds` |
| `pm_debris_laser_broom` | `cat_star_purple_p2.dds` | a ground observatory dome firing a thin green laser beam up at a tiny tumbling fragment | `gfx/interface/icons/production_method_icons/debris_laser_broom.dds` |
| `pm_debris_fusion_sweepers` | `cat_rocket_purple_p5.dds` | a fusion-drive tug with a wide mesh net gathering debris in orbit | `gfx/interface/icons/production_method_icons/debris_fusion_sweepers.dds` |
