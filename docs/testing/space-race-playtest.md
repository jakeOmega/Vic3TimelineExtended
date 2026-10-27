# Space Race play-test checklist

What the next play-test of the space race should look at. In-game checks don't gate the merge (CLAUDE.md, "In-game checks"). Launch windows and orbital debris have their own list in `docs/testing/global-commons-playtest.md`.

## Progress in months (2026-10-25)

Every event that moves a milestone's progress moves it by whole months of the programme's pace, recorded when the event fires (`docs/systems/mod_systems.md` → Space Race → *Progress in months*). Nothing here rests on an unverified engine fact (the pace is a `set_variable` of a script value, the amount an inline script value in `change_variable`), so there is no self-check; these are display and feel checks.

1. **A setback's tooltip.** Run a milestone at a pace you can read on the overview (the headline's "+N/mo"), then fire a setback (`event te_debug_space_race.1` option j, or wait for the roll). Each option reads "Lose N months of this milestone's progress (-X)", with X = N × the pace to one decimal, and not 0. A minor setback (Safe or Standard) offers 1 to 4 months, an Ambitious failure 4 to 6. On Ambitious the pace, and so X, is half again as large.
2. **The bar drops by what the tooltip said.** Pick an option and read the milestone's progress before and after: it falls by X, or to 0 when the milestone had less than X. On Solar System Colonization with fleets staged in orbit (more than one goal of progress), it falls by X and never by more than one goal.
3. **Funding while the event waits.** With a setback open, cut every milestone's funding to 0, let a day pass, and pick an option: the tooltip and the loss still use the pace from when the setback struck. The same for a windfall (event `.49` or `.50`) after raising funding.
4. **Windfalls.** An in-progress event (`.30`, `.40`, `.49`, `.55`, …) reads "+N months of mission progress (+X)" and every milestone it names gains X. The gambles (`.44.b`, `.46.b`, `.54.c`) show each outcome's months under its chance.
5. **The notice.** When another power completes a milestone, the notice's first option reads "+1 month of mission progress" and moves every milestone we have under way by our pace.
6. **The panel's text.** How the Space Race Works → Setbacks describes months, not percentages, and the Setback Risk concept says a setback loses some months of progress.

## The Space Race tab between milestones (2026-10-25)

The Timeline Extended window's Space Race tab stays open once the country is in the race, and opens with Space Powers and Orbit (`docs/systems/mod_systems.md` → Space Race → *The tab's own sections*). No self-check: everything here is display, and each item fails visibly (an empty row, a raw key, a blank name). Three accessors are new to the mod and are named with their fallback.

1. **The tab stays open.** Complete Suborbital Flight with Orbital Flight not yet possible (no Guided Missiles): the tab stays enabled, its Milestones note shows, and How the Space Race Works is still at the foot. Start Orbital Flight: the note goes and the milestone's block appears.
2. **Our row (`GetPlayer.GetCapital` as a datacontext: new).** The first Space Powers row names us, with our programme's eight icons matching the overview's Programme row and "<milestone>: N%" equal to that milestone's own progress. If the row is blank, store our capital in the monthly refresh (an `sr_power_self` slot) and read it like the others.
3. **The other powers.** Before the first monthly pulse after the tab opens (or on a save from before this change), the note "listed from the start of next month" shows; after it, the rows. Each row's name, icons and hovers are that power's, in the third person ("achieved, first in the world"); the estimate's band is the Rivals rows' for the same rival and milestone (open a milestone we both run and compare). Since audit SPC-9 every power is a row (see the next section).
4. **The debris row on the tab.** Its loc now roots on `GetPlayer` instead of `JournalEntry.GetCountry`: it reads the same in Mission Control and in Orbit, hover included.
5. **The last strike (`global_var:<country> = { save_temporary_scope_as }` printed through `SCOPE.sCountry`: new).** Strike someone (at war, with Guided Missiles and a Space Program), then hover Anti-Satellite Strikes So Far: "The last: <us> struck the satellites of <them>, 0 months ago". If the names are blank, print each country from inside its own `global_var:` scope (`[THIS.GetCountry.GetName]`, the Cultural Hegemony leaderboard's form) on two lines.
6. **Our satellites.** On the target's side (switch to it, or have an AI strike us): Disrupted, with the months left and the modifier's effects on hover; after the disruption, Intact with the cooldown's months; with no Space Program or orbital megaproject, None in Orbit.
7. **Our strike (`IsValid` read from loc, where the window's tab tooltips read it from `.gui`).** Not Ready before Guided Missiles or with no Space Program, the hover listing what is missing with ticks and crosses; Ready after, the hover listing every enemy with something in orbit, a struck one marked with its months.
8. **Cost.** Late game, with Space Powers and Orbit open, the frame rate holds (the rows read a code and the icons' values per frame; Our Satellites walks our buildings).

## The GUI audit wave (2026-10-27)

The space race panel's share of the GUI and localization audit (`docs/audits/gui_audit/space_seabed.md`, SPC-1 to SPC-19). Colonization's own items are in `docs/testing/solar-colonies-playtest.md` under the same date, the Seabed tab's in `docs/testing/global-commons-playtest.md`.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK OK sr_powers_list country=… powers=N listed=N` | once a game, the first monthly refresh of a player in the race with 2 to 40 other powers | the Space Powers list holds every other power: `ordered_country` with `min = 0`, `max = 40`, `check_range_bounds = no` walked the whole field, so the Rivals lists, built the same way, do too | `listed` differs from `powers`: the walk stopped short (or went past) | go back to fixed slots filled one position at a time (`ordered_country` with `position = N`, the count checked first), as `sr_power_slot` / `sr_rival_slot` did before audit SPC-9 (git history), and draw them as rows again |

### Checklist

1. **Space Powers and Rivals as lists (datamodels of capitals, `Scope.GetState` then `State.GetCountry` on each item: new in this combination).** With three or more other powers in the race, Space Powers shows every one as a row, furthest along first, each with its name, its eight icons and its band; nothing reads "+N more". A milestone's Rivals lists every rival the same way, each with its bar, marker and band in words. If the rows are blank or show one power over and over, the accessor chain failed: go back to the slots (the self-check's fallback).
2. **The rows' hovers (`GetPlayer` inside an item's tooltip).** Hover a rival's row: its name, the estimate concept, the band and the marker, with figures, not blanks. Hover a power's name and its icons: third-person states and the achieved count.
3. **Before the first refresh.** On a save from before this change, or the first month of a milestone: Rivals reads "No other power is working on this milestone at the moment" until the next month, then the rows; Space Powers reads "listed from the start of next month".
4. **The tab's order (owner, 2026-10-27).** The tab opens with the running milestones, each with its overview, Mission Control and Rivals, then Space Powers, Orbit and How. The debris row shows once, in Orbit, not in the tab's Mission Control; the journal entry's own Mission Control still has it.
5. **Greyed buttons say why (`IsValidTooltip`, a break, `ExecuteTooltip`).** Hover a greyed Safe or Ambitious, Funding −/+, Emigration −/+ at its end, Launch with an empty reserve, Auto, a build-mix button: the requirements first, ticked or crossed, worded as requirements ("The fleet is not refitting"), never a raw trigger name; then what the button does.
6. **Concepts.** In the colonization tooltips, the concept names (Module, Space Fleet, Ship Role, Space Command, Drive, Launch Window, Colony Autonomy, Free Colony, Blockade, Integrity, Marines, Program Estimate, Colony Fleet, Anti-Satellite Strike) are links; the Defenses tooltip leads to Space Fleet, then Ship Role, then Space Command.
7. **Type sizes (17 rows, 20 headings, 16 overview).** Nothing elides at 100% UI scale in the overview (Safe and Ambitious now carry the weekly cost on a second line), the fleet and location rows, the module cells, the queue and the Colony Fleets rows. Note any "…" with the text it cut.
