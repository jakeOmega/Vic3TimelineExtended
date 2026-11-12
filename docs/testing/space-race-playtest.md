# Space Race play-test checklist

What the next play-test of the space race should look at. In-game checks don't gate the merge (CLAUDE.md, "In-game checks"). Launch windows and orbital debris have their own list in `docs/testing/global-commons-playtest.md`.

## Progress in months (2026-10-25)

Every event that moves a milestone's progress moves it by whole months of the programme's pace, recorded when the event fires (`docs/systems/mod_systems/space_race.md` → Space Race → *Progress in months*). Nothing here rests on an unverified engine fact (the pace is a `set_variable` of a script value, the amount an inline script value in `change_variable`), so there is no self-check; these are display and feel checks.

1. **A setback's tooltip.** Run a milestone at a pace you can read on the overview (the headline's "+N/mo"), then fire a setback (`event te_debug_space_race.1` option j, or wait for the roll). Each option reads "Lose N months of this milestone's progress (-X)", with X = N × the pace to one decimal, and not 0. A minor setback (Safe or Standard) offers 1 to 4 months, an Ambitious failure 4 to 6. On Ambitious the pace, and so X, is half again as large.
2. **The bar drops by what the tooltip said.** Pick an option and read the milestone's progress before and after: it falls by X, or to 0 when the milestone had less than X. On Solar System Colonization with fleets staged in orbit (more than one goal of progress), it falls by X and never by more than one goal.
3. **Funding while the event waits.** With a setback open, cut every milestone's funding to 0, let a day pass, and pick an option: the tooltip and the loss still use the pace from when the setback struck. The same for a windfall (event `.49` or `.50`) after raising funding.
4. **Windfalls.** An in-progress event (`.30`, `.40`, `.49`, `.55`, …) reads "+N months of mission progress (+X)" and every milestone it names gains X. The gambles (`.44.b`, `.46.b`, `.54.c`) show each outcome's months under its chance.
5. **The notice.** When another power completes a milestone, the notice's first option reads "+1 month of mission progress" and moves every milestone we have under way by our pace.
6. **The panel's text.** How the Space Race Works → Setbacks describes months, not percentages, and the Setback Risk concept says a setback loses some months of progress.

## The Space Race tab between milestones (2026-10-25)

The Timeline Extended window's Space Race tab stays open once the country is in the race, and opens with Space Powers and Orbit (`docs/systems/mod_systems/space_race.md` → Space Race → *The tab's own sections*). No self-check: everything here is display, and each item fails visibly (an empty row, a raw key, a blank name). Three accessors are new to the mod and are named with their fallback.

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
6. **Concepts.** In the colonization tooltips, the concept names (Module, Space Fleet, Ship Role, Space Command, Drive, Launch Window, Colony Autonomy, Free Colony, Blockade, Integrity, Marines, Program Estimate, Colony Fleet, Anti-Satellite Strike) are links; the Defenses tooltip leads to Space Fleet, then Ship Role, then each role (Warship, Rapid Response Ship, Siege Ship, Assault Carrier, Tender) and Space Command. Each build-mix button's hover names its role as a link, and a plural link ("Siege Ships") reads right.
7. **Type sizes (17 rows, 20 headings, 16 overview).** Nothing elides at 100% UI scale in the overview (Safe and Ambitious now carry the weekly cost on a second line), the fleet and location rows, the module cells, the queue and the Colony Fleets rows. Note any "…" with the text it cut.

## The GUI audit backlog: colors carried inline (2026-10-27)

`unmarked_hover_audit` went into CI on 2026-10-27, and the Space Race's status words and figures with a hover took `default_format = "#tooltippable"` from their type, with their color moved inline into the loc or the generated row (`#R Blockaded#!`, `#v …#!`). On 2026-10-30 the owner retired the rule and the audit (`gui_style_guide.md` rule 3: vanilla underlines almost none of its hovers) and the Space Race panel lost its underlines; the colors stay inline.

1. **Colors without underlines.** On the Solar System, Colonies (People, Defenses) and Fleets views, look at a red status word (Blockaded, Occupied, Battle), a grey Ruined, a highlighted figure (a colony's people, a fleet's strength) and a plain one (Δv, supply). Each keeps its color (red, grey, the value color) with no underline, and its hover still opens. If a word shows cream, its inline color lost to the textbox's format: put the color back in the textbox's `default_format`.
2. **Approach tooltips.** Hover Safe and Ambitious on a running milestone: the line of framing, then the approach modifier's own lines (risk −50%, or progress +50%).

## The Space Program in the capital (2026-11-03)

The Space Program now stands in its owner's capital (`sr_space_program_site`, `space_race_triggers.txt`: `owner.capital ?= THIS`), for every country. It was the market capital of a market the owner led, so a customs-union member could never found one.

1. **Founding it as a customs-union member.** As a great or major power in another country's customs union, with Guided Missiles: Found a Space Program is possible, and the building appears in our capital, running Earth Orbit, and still stands two months later (the monthly `remove_invalid_buildings` sweep spares it).
2. **A market capital that is not the capital.** As the USA (market capital New York, capital Washington), found one: it stands in Washington. The build menu lists only the capital, and the greyed reason on other states reads "This state is our capital".
3. **Space Command's tie.** With two Space Commands of the same size after an annexation, the one in the capital stays.

## One report per loss, one notice per achiever (#448, listed 2026-11-12)

Two checks carried from #448 (the fixes of #441). Since 2026-11-06 a programme loss concludes the milestones it hits (the section below), but the report is still queued once (`sr_report_program_loss`), so the first check stands as it was written.

1. **One Silent Gantry for one loss.** Run two milestones (Suborbital Flight and Orbital Flight), then remove the Space Program (`event te_debug_space_race.1`, option l). Exactly one The Silent Gantry opens, about five days after the first entry fails, and it lists both milestones. Two popups: the entries' failures fell more than five days apart, or `sr_program_loss_report_queued` did not hold.
2. **Two named notices from a dotted list target.** `event te_debug_space_race.1`, option k: two other powers report Suborbital Flight. Fourteen days later two Eclipsed (`space_race_events.20`) open, each naming its own power. One popup, or a blank name: `add_to_variable_list`'s `target = scope:sr_achiever.capital` did not take the dotted chain (`sr_notify_milestone_achievement`); save the capital as a scope of its own first.

## An idle Solar System Colonization's approach (2026-11-06, #1472)

Solar System Colonization's entry stays open for its colonies after its programme stops, and its approach declarations now also need the programme billed (`sr_milestone_billed_solar_colonization`), as its cost and funding declarations already did.

1. **The approach goes with the programme.** Run Solar System Colonization on Ambitious beside another milestone, and note that milestone's pace. Switch the Space Program's colonization method off and wait a week: `sr_ambitious_approach` leaves the solar entry (hover its modifiers), the other milestone's pace falls by the +50%, and the solar overview reads Idle. Switch the method back on: within a week the modifier is back, and so is the pace.

## A milestone starting again after a programme loss (2026-11-06)

A lowered Space Program method or a lost building fails every milestone the launch complex can no longer carry (the failure outcome of each `je_space_race_<m>`; `docs/systems/mod_systems/space_race.md` → *Programme loss (`.76`)*). The engine deletes a concluded record three days later and never activates that type again (`docs/guides/scripting_best_practices.md`, "A finished record is deleted": the Colonial Empire's 1910 save), and nothing added a milestone back, so a refit ended it for good. Not seen in a save of our own yet: the second self-check below confirms or refutes it. A monthly pass now adds the entry back (`sr_reentry_monthly`, `common/scripted_effects/space_race_effects.txt`, run from `space_race_on_action` after the inactive-milestone cleanup) once the country has been due it for a whole month (`sr_reentry_due_<m>`, `space_race_triggers.txt`: no record of it, active or inactive, not decentralized, not a revolution's rebels, and the entry's own `is_shown_when_inactive` and `possible`, so the method can carry it again). It starts from zero: the progress lost at the failure stays lost (owner, 2026-11-06). Search `debug.log` for `sr_reentry` and `sr_closed_record`.

### Self-checks

| Name | What it checks | Where | If BROKEN |
|---|---|---|---|
| `sr_reentry` | `add_journal_entry` brings back a milestone the country has finished (no vanilla precedent re-adds a finished type; the Colonial Empire's `ce_reentry` asks the same question and was unanswered on 2026-11-06). The failure cleanup marks the milestone closed, naming the country (`sr_closed_by_loss_<m>`). The pass marks each add, naming the country, and the next monthly pass reads the mark before it can add again: OK when the entry is running (active with `sr_active_<m>`), BROKEN when it is not though the country is still due it. Judged only with both marks naming the country, so a save from before this change (its milestones closed with no mark) gets the add and no verdict. Once a game for each verdict. | `TE_SELF_CHECK OK|BROKEN sr_reentry milestone=<m> country=…` in `debug.log`, a month after the add | `add_journal_entry` cannot bring a finished type back. Stop the milestones concluding on a programme loss: drop each failure outcome, so the entry deactivates instead (`can_deactivate = yes`, and its `possible` requires the method), keeping its record, which the engine re-activates itself (proven: the Map Room, `journal-map-modes-playtest.md` item 5); have the monthly cleanup (`sr_cleanup_inactive_space_race_milestones`) queue `.76` for a milestone whose method is gone; retire the pass. |
| `sr_closed_record` | The bug itself: a milestone closed on a programme loss never comes back by itself. OK at an add to a country with the closed mark: the method has carried the milestone for a whole month (at least two of the engine's fortnightly updates) and the country holds no record of it. BROKEN when a milestone with the mark is running again and the pass did not add it. A revolution's winner drops its marks (it holds fresh records), and "running" needs `sr_active_<m>`, which the failure cleanup removed, so a concluded record not yet deleted never reads as running. Once a game for each verdict. | `TE_SELF_CHECK OK|BROKEN sr_closed_record milestone=<m> country=…` in `debug.log`, at the add | The engine re-activates a concluded milestone: the pass is idle (its record tests stop it), so nothing breaks. Correct "A finished record is deleted" in `scripting_best_practices.md` for this case and retire the pass. |

### Checklist

1. **A lost building.** As a great or major power running Suborbital Flight (or Orbital Flight), push it to 90% (`event te_debug_space_race.1`, option a), then remove the Space Program (same event, option l). Within about nine days The Silent Gantry fires and lists the milestone as closed; the entry is gone from the journal. Found a Space Program again (the decision). Within two months the milestone is back in the journal at 0%, funding 1 and Standard, and `debug.log` has `TE_SELF_CHECK OK sr_closed_record milestone=suborbital` (at the add), then `TE_SELF_CHECK OK sr_reentry milestone=suborbital` a month later. If it is back within a month of the decision with no `sr_closed_record` line, read `TE_SELF_CHECK BROKEN sr_closed_record`: the engine brought it back itself.
2. **A refit.** Running the Moon Landing (Moon Mission), switch the Space Program to Earth Orbit in the building panel: Program Discontinued fires and lists the Moon Landing (and the Deep-Space Probe if it ran). Switch back to Moon Mission (or take Begin the Moon Mission): within two months the Moon Landing runs again from 0%, and the landing-site choice is not asked a second time (`sr_moon_landing_choice_made`).
3. **One entry, not two.** Drop below major power while a milestone runs (it deactivates and keeps its record, as before), then regain the rank: the milestone comes back within two weeks, as before, with no `sr_reentry` line and one entry in the journal. Two entries: the pass added on top of a record; its `has_inactive_journal_entry` test did not hold.
4. **Colonization without a colony.** With no colony yet and Solar System Colonization running, lower the method below Solar Colonization: the programme closes (its whole staged fleets are kept, `sr_launch_banked_fleets`). Raise it again: within two months the programme runs again, and its next launch month restores the banked fleets.
5. **The AI.** In an observer game into the 2000s, note any `TE_SELF_CHECK` line for `sr_reentry` or `sr_closed_record`: an AI that refits its Space Program down and back up should get its milestones back the same way.

## First and later completion outcomes (2026-11-12, #1433)

Each milestone from Suborbital Flight to the Interstellar Probe has two completion outcomes, first and later, ahead of the failure outcome (`je_space_race.txt`; `docs/systems/mod_systems/space_race.md` → *"The First" Bonus*). Offline checks cover the script; these need the game.

1. **The panel.** Open a running Suborbital Flight before anyone has finished it: the outcomes list reads First into Space, Edge of Space Reached, then the failure. Each shows its trigger (the goal, then "No other country has achieved this milestone yet" or "Another country has already achieved this milestone") and its reward modifier under its effect header. The first outcome's trigger line is met and the later one's is not.
2. **First.** Finish it first (`event te_debug_space_race.1` to push progress): the entry concludes through First into Space, the concluded page reads "... ahead of every other country", and the reward is `sr_first_suborbital`.
3. **Later.** In another game, or as a second power, finish a milestone another country has already finished: the entry concludes through the later outcome with the old conclusion text, and the reward is `sr_<m>`.
4. **A tie.** In an observer game, if two powers finish the same milestone on the same update, note which outcome each concluded through and which reward each holds. Expected: only one holds `sr_first_<m>`, whatever the outcomes say. If both concluded through first, the second's concluded page claims a first it did not win (its reward is still the later one); record how often, so the owner can judge whether that is worth a fix.

