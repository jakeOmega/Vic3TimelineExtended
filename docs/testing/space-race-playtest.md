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
