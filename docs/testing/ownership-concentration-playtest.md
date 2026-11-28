# Ownership concentration: play-test

Financial Districts and company headquarters hire their owners as a fixed partnership plus a
smaller part a level, so a larger district or company has fewer owners a level and each one holds
more. Dynastic Wealth reads it through a new target term, Scale of Fortunes. Scope and the owner's
calls: `docs/superpowers/specs/2026-11-28-ownership-concentration-scope.md`. How it is built:
`docs/systems/mod_systems/production_methods.md` § Ownership buildings and
`docs/systems/mod_systems/demographics.md` § Dynastic Wealth per state.

The sizes are provisional (owner, 2026-11-28: "ok" to settling them on saves). Each owner line T a
level became 6T in `unscaled` and 0.4T a level: a building breaks even with the old staff at level
10 and keeps 40% of it a level beyond. Item 5 below is the measurement that sets them.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … ownership_partners` | once a game: the first yearly country pulse of a country with a Privately Owned Financial District of level 5 or more | its capitalist positions read 300 + 20 a level, within 5% (`capitalists` against `expected`): the partnership is hired once a building, as `ai_managed_flat_staff` read for production buildings | about 320 a level: `unscaled` employment is read per level on an ownership building, and the district hires 16 times its old owners a level. About 20 a level: the partnership isn't summed there. Confirm in the building panel before taking the fallback | in `extra_pms.txt`, put each partnership back on its per-level line (the owners' old figure, 2.5 times the per-level part) and drop the `unscaled` owner lines; `test_ownership_partnership.py`'s `PARTNERS` to 0 and `PER_LEVEL` to 1 |
| `TE_SELF_CHECK … ownership_assets` | once a game: the first yearly country pulse of a country with a district or private headquarters that owns Light Industry levels | of that building, `num_building_assets_of_group(bg_manufacturing)` is at least the `bg_light_industry` count (`bg_manufacturing` ≥ `bg_light_industry`): a parent group's count includes its children's, so `te_demog_building_owned_levels`, which sums the nine top-level groups, reads every level the building owns | `bg_manufacturing` under `bg_light_industry`: a count is of the group's own buildings only, so Scale of Fortunes reads too little property, mostly 0 | sum every group that is some building's own `building_group` instead of the nine top-level ones (`te_demog_values.txt`; the test's group check moves with it) |

A third line, `TE_INFO demog_fortunes_centre`, logs the world's figure once a game (`levels`, `owners`, `per_1000`), at the game's start or, in a save from before the change, at the first state's yearly pulse. It changes no number. With no line in a new game's first month, the first day's buildings read no owners or no property, and the term waits for the next try 30 days on.

## In the game

1. **A large district.** Find a Privately Owned Financial District of level 20 or more. Its capitalist positions read 300 + 20 × its level (700 at level 20, against 1,000 before), its shopkeepers, clerks and academics as before. A level-1 district reads 320.
2. **A company.** A capitalist-owned headquarters hires 150 capitalists + 10 a level, its clerks and academics as before. Check that a company that grows hires fewer capitalists a level.
3. **The tiers.** With Transistors, a capitalist-owned headquarters offers its own Electronic Brokerage (one option, not the District's), and keeps 150 + 10 capitalists a level with 12 clerks and 3 academics a level. An aristocrat-owned headquarters offers one too, and keeps its aristocrats. Under Command Economy or Cooperative Ownership no headquarters offers a tier. A headquarters that ran the District's tier before the update drops to its category's base method and may take its own tier again (unread: the game's handling of a method that became invalid).
4. **Divine Economics.** Under principle IV or V, an aristocrat-, shopkeeper-, academic- or bureaucrat-owned headquarters offers its own Increased Clergy Oversight, as under II and III. Of the six copies, a headquarters offers only its own category's: until 2026-11-28 the capitalist copy had no category gate.
5. **The sizes (M1 and M3 of the scope).** On an 1890, a 1950 and a 2050 save, read the distribution of district and headquarters levels (median and the top tenth), and the capitalists a country employs against the same save before the change. If most districts sit below level 10, the partnership puts more owners into small buildings than before and the break-even should come down. Watch the Industrialists' clout: fewer, richer capitalists could weaken it, the reverse of what concentration should do.
6. **Scale of Fortunes.** The Demographics tab's Wealth section and the state panel's Dynastic Wealth tile list the term under What Sets the Target. In a new game it reads about 0 for the world as a whole in 1836, and positive in states whose districts and companies are large. It stays within −5 and +10.
7. **Old saves.** In a save from before the change the world's figure is measured from the save itself at the first state pulse after loading, so the term averages about 0 across the world, though a state with larger districts and companies than the world's reads above 0; its score follows at 3% of the gap a year. Big late-game districts lay off capitalists over a few weeks. Check that those capitalists find other work rather than leaving a lasting pool of unemployed capitalists.
