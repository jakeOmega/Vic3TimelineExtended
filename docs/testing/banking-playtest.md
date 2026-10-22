# Banking play-test checklist

What the next play-test should look at in the banking cycle. In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here.
Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Logs.** Read `debug.log`, not `error.log`, for the self-check lines; `error.log` carries the script errors.
- **Saves.** `scripts/analysis/save_country_probe.py <save> --tag <TAG> --var '^(banking_crisis_wave_|banking_contagion_|crash_severity|contagion_crash|finance_cycle_)'`
  reads a country's banking state without the game. The contagion event's options leave modifiers whose start
  dates give the cascade tier: a pulse's contagion events land on the 7th (reached by the crash that started the
  wave), the 14th (by a first-tier crash), the 21st and the 28th.

## Self-checks (every game)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … contagion_one_open` | BROKEN once a game, when a contagion event opens for a country that already has one open. OK once a game, when a contagion event closes alone after a wave that reached its country while it was on its way or open was turned away (`turned_away=N`); a game with no such reach logs no OK | one contagion event per country at a time: the mark the spread sets when it sends the event (`banking_contagion_pending`) turned the second wave away, and the event answered for both | two contagion events open at once, so two rolls and two popups again; the line gives `date`, `open` and `turned_away`. Find both events for that country in `debug.log`. Within a week of loading a save made before the block, it can be a pair sent under the old rules: no fault. If the first had been open more than 120 days, the mark ran out under it. If both were sent while the mark stood, something sent the event past the spread, or removed the mark (a loyalist win re-running `je_banking_cycle`'s `immediate` would) | Mark ran out: raise `days` in `banking_contagion_mark_pending` above the event's real lifetime. Mark not seen or removed: make the mark untimed and count monthly passes instead, as `covert_open_event_stale_passes` does, or drop the revolution clear in `je_banking_cycle`'s `immediate` if a loyalist win caused it. The event `trigger` the owner sketched first (a mark set in `immediate`) is no fallback for the same-pulse case: both copies are sent before either opens |
| `TE_SELF_CHECK … contagion_roll_scope` | Judged only for a contagion event that was alone: no other copy open for the same country between its roll and its answer (`open=1`), which since the block (`contagion_one_open`) is every one. OK once a game, when the first country a contagion cascade reached (a contagion crash spreading on, not an origin crash) has its own roll crash; BROKEN each time a lone event's options and its roll disagree. A copy open beside another is not judged: `contagion_one_open` reports that | the event's own `save_scope_as = contagion_crashed` replaced the upstream country's inherited one, so a cascade target's crash plays as a crash. The 2026-10-17 autosave already shows this: targets two and three tiers out had taken the crash-only options | `roll=crash read=scare open=1`: the save did not replace the inherited scope, so in a cascade only the first tier can crash. `roll=scare read=crash open=1`: a scare took the crash options, the 2026-10-16 bug. A country whose copy never resolved (annexed first) is not judged until the spread sends it the next one | A BROKEN with `open=1`: drop the saved scope and read the roll from `var:contagion_crash` in the text, options and cascade. With one contagion event at a time the variable is the event's own roll, so this no longer changes play. The old fallback, a saved scope *value* set on both outcomes, stays withdrawn: it needs the same replacement, and where that fails a scare inherits the upstream country's crash, the 2026-10-16 bug |
| `TE_SELF_CHECK … banking_entry_everywhere` | Once a game, 30 days after the first yearly pulse (an old save's first after this change) | every country that should hold `je_banking_cycle` (under the rule, not decentralized, not a rebel) does, and the safety net added none: the engine activated every record | `missing=` countries still without it (each named on a `TE_SELF_CHECK INFO … missing:` line after it), `added_by_net=` how many the net has added (each logged as `TE_BANKING: the safety net added …`). The engine left records out (or, for `missing`, a country formed in the last two weeks); the net carries them, a month late at most. **Read BROKEN `missing=3 added_by_net=0` on August 4, 2045 in the owner's EU game (2026-10-17), so the fallback below is in: the net runs monthly** | ~~Add the entry from a monthly pulse instead of the yearly one (`te_banking_entry_net` in `te_banking_entry_on_actions.txt`), so a country waits a month at most~~ (done 2026-10-17). Next: a `TE_BANKING: the safety net added` line for each named country within a month says the net carries them. A named country the net never adds, while still named a month on, means `add_journal_entry` fails for it: read its type and status in a save |

## A contagion scare plays as a scare (2026-10-16)

The European Union (cooperative economy, bubble pressure 0) got the contagion event and its cycle fell from 59.9 to 30.
Its save shows the roll was a scare (`banking_crisis_wave_scared`), yet the crash branch ran, at the tier of a
`crash_severity` of 25 left by an earlier crash, and the cascade ran from it (`banking_crisis_wave_counted`). The event's
saved scope `contagion_crashed`, which marks a crash, had come in from the upstream country, and `clear_saved_scope`
did not remove it. Every read now asks that the saved country be the event's own (`banking_contagion_own_roll_crashed`).

1. **A scare is a scare.** Under a cooperative economy, a scare takes 2 cycle value and 0.5 momentum; under a command
   economy 1 and 0.5; otherwise 3 and 1. It offers only "Close the gates" and "Maintain open markets", and the history chart gets no
   red crash marker that month.
2. **A crash is still a crash, and spreads.** A country whose own roll crashed sees the crash-only options (capital controls,
   monetary intervention, confidence messaging where its laws and institutions allow), takes a crash tier, and its
   neighbours get contagion events a week later.
3. **No `crash_severity` errors.** `error.log` has no `Failed to fetch variable for 'crash_severity'` from
   `banking_cycle_effects.txt` (the crash tiers, or the spread's severity weights) during a wave.
4. **The Great Depression waits for real crashes.** The wave count rises only with countries that crashed: a wave
   should rarely reach the event's ten countries now, where before every country a cascade touched counted.

## An event that resolves just after a revolution (2026-10-16)

`banking_cycle_post_event_refresh`, the end of nearly every banking event, now skips the phase modifiers and bars when
the country holds no `je_banking_cycle`. Bunyoro's contagion event resolved two seconds after its revolution ended,
before the winner had taken the entry over, and every `je:` read failed.

5. **No `je` errors after a revolution.** In a game with revolutions during a banking wave, `error.log` has no
   `Failed to scope to journal entry by tag 'je_banking_cycle'` from `banking_cycle_effects.txt`, and the winner's
   banking bars are right by the next month.

## Two contagion events open at once (2026-10-17)

The observer run of 2026-10-17 (1836 to 1898) logged five `contagion_roll_scope` BROKEN lines, four
`roll=scare read=crash` and one `roll=crash read=scare`. None was the engine. Every country's banking pulse runs on
the same day, and a second origin crashing in that pulse re-runs `banking_crisis_wave_init`, which clears every
reached mark, so a country can be reached twice: Austria took a scare on 1898.8.7 and, reached again by a
first-tier crash, a crash on 8.14. When both origins reach it in the pulse itself, two copies of the event are open
at once. They share `contagion_crash`, the later roll overwrites the earlier one's, and the earlier copy's check
compared its own roll with the other copy's. The options had followed each copy's own roll. The check now counts
the copies open (`banking_contagion_open`) and judges only a copy that was alone; the title, description and
flavour read the event's own roll, as the options do.

6. **No `contagion_roll_scope` BROKEN.** It judges every contagion event now, since one is open at a time
   (below), and logs its OK once. The NO_VERDICT lines are gone: a second copy open is `contagion_one_open`'s
   BROKEN. A BROKEN with `open=1` is real: take the fallback in the table.
7. **The text matches the options.** A country whose own roll crashed reads "Cascading Financial Collapse" and the
   cascade description and sees the crash-only options where its laws and institutions allow; a scare reads
   "Contagion from Abroad" (or "Financial Contagion" after a severe crash) and gets only "Close the gates" and
   "Maintain open markets". Two at once should no longer happen (item 8).

## One contagion event at a time (2026-10-17)

The owner's call on the double events above: "Ideally, only one." The spread now marks a country when it sends
it the contagion event (`banking_contagion_pending`, 120 days), and turns away any later reach while the mark
stands. The event sets the mark again when it opens, and its `after` removes it. `banking_crisis_wave_init` leaves
the mark alone, so a second origin crashing in the same pulse no longer sends a country a second event. The
turned-away wave marks the country reached, with the open event's outcome if it has rolled, and the event counts
toward the Great Depression only through its own crash, once. A revolution's winner drops the mark, since the
event died with the loser.

8. **One popup.** When two crashes in one month reach the player's country, it gets one contagion event; while
   that event is open, further crashes pass it by. Once it is answered, a later crash can reach it again.
9. **`contagion_one_open`: no BROKEN, OK once.** The observer run of 2026-10-17 had about five double reaches in
   sixty years, so a long observer game should log the OK, with `turned_away=1` or more.
10. **The mark goes.** After a wave, `save_country_probe.py --var '^banking_contagion_'` on a country that answered
    its contagion event shows no `banking_contagion_pending`. After a rebel win during a wave, the winner shows
    none either.

## Scare only for a year; the origin counted once (2026-10-17)

The owner's calls. **"Scare only for a year":** a crash zeroes bubble pressure, but the contagion roll still weighs a
crash at 5 to 30 points of the origin's severity against 100 for a scare, about 5 to 23% at zero bubble in a market
economy. Every crash, an origin's or a contagion's, now sets `banking_crashed_last_year` for 365 days where it is
decided, beside `banking_recent_crash`, and while it is set the contagion roll is skipped: the event plays as a scare
and marks the country `banking_crisis_wave_scared`. A country with a low bubble that has not crashed keeps the 5 to 30
floor. **The origin is counted once:** `banking_crisis_wave_init` marks the origin `banking_crisis_wave_counted`, so a
contagion event it still holds from an earlier wave cannot count it a second time toward the Great Depression.

11. **A crash shelters a country for a year.** A country that crashed, at home or by contagion, and is reached again
    within the year gets "Contagion from Abroad" (or "Financial Contagion" after a severe crash) with only "Close the
    gates" and "Maintain open markets", whatever its bubble. `save_country_probe.py --var '^banking_crashed_last_year'`
    shows the marker on it.
12. **No contagion crash within a year of a crash.** On any country's history chart, a contagion crash marker never
    comes less than twelve months after another crash marker, its own or contagion's. After the year, contagion can
    crash it again. The rule is contagion's only: a country's own crash still depends on its bubble alone.

## Every country holds the banking entry (2026-10-17)

The entry is every country's from the first weeks of a game, dormant until its financial cycle starts: Stock Exchange and
an Urban Center of level 5, the test that used to activate the entry
(`docs/superpowers/archive/specs/2026-10-17-banking-always-on-design.md`).

13. **A new game.** Within two weeks every country's journal holds the entry, and the Banking tab opens for all of them.
    A country without Stock Exchange or a level 5 Urban Center shows the Not Started cell (its hover the two conditions,
    ticked or crossed), its Monetary Policy readings with every control greyed under the read-only note, and Available
    Interventions with every Enable greyed under its note. No bars, no Active Policies, no history, no phase in the top
    bar.
14. **The start.** The month a country meets both conditions, its cycle appears at Stable with no momentum and no bubble,
    the controls and tools open, and a human player gets the Banking Cycle Begins notice. A country that meets the test
    in 1836 starts when its entry activates, with no notice.
15. **An old save.** Countries that already ran the cycle carry on unchanged. The rest get a dormant entry within two
    weeks, and the self-check line reads OK.
16. **A dormant central bank.** A country with a National Bank but no running cycle keeps the Dual Mandate (or its act's
    mandate under Central Bank Independence), and its dial can't be moved until the cycle starts.
17. **Rebels.** During a revolution the rebels hold no banking entry. When they win, the nation's cycle carries on where
    the loser left it.
18. **No new errors.** `error.log` has no `Failed to fetch variable` for `finance_cycle_value`, `finance_cycle_momentum`
    or `bubble_pressure` while a dormant entry's panels are open, or from the AI's banking buttons.

## Hover on the overview's readings (2026-10-18)

The word under each overview caption (and both words of the Budget cell) has a tooltip of its own, saying what that
reading does. The cell's old tooltip is unchanged and still shows over the caption, the icon and the cell's blank
space. Two engine facts rest on the pattern's other uses and have not been seen in this arrangement: a
`[GetStaticModifier('x').GetDesc]` inside a key that `GetCustom` returns, and the underline of `#tooltippable` under a
coloured word (`#green Expansion#!`).

19. **Each word is hoverable.** Underlined, six cells: Cycle Phase, Momentum, Bubble Pressure, Budget (the used line and
    the free line separately), Policy Stance (needs a dial) and Inflation (full Banking System). Hovering the word shows
    its own tooltip; hovering the caption or the icon still shows the cell's. *Fallback if the coloured words lose their
    underline:* the hover still works; drop `default_format` from the coloured words (phase, momentum, bubble) only.
20. **The phase shows its own economy's modifiers.** In a market economy, Expansion reads "Financial Cycle: Expansion"
    and lists services output, manufacturing, the investment pool, bubble pressure and momentum; under Command Economy
    it reads "Planning Cycle: Expansion" with construction and bureaucracy; under Cooperative Ownership "Cooperative
    Cycle: Expansion" with the investment pool. The figures equal the ones in the journal entry's modifier list for the
    phase. Stable lists no modifier. Panic, Downturn and Stagnation call a crash all but impossible; Frenzy the highest
    risk. *Fallback if the effect list is blank or shows raw text:* move the economy choice into the `.gui`
    (`SelectLocalization` over three tooltip keys per word) so `GetStaticModifier` is in the tooltip's own key.
21. **Momentum and bubble pressure.** Momentum's first line gives the band's range ("Rising: momentum is +1 to +3 …");
    in a Boom or Frenzy, Surging and Overheating match the crash-risk warning on the bubble icon. Bubble pressure's
    text changes with the band and the first line names it.
22. **Policy stance and the price band.** The stance's tooltip repeats the cell's momentum and bubble pushes and adds
    the stance modifier (Neutral: "None"). The price band's tooltip gives the band's prose and, under "Modifiers on your
    country", the figures that match the country's modifier list; Stable prices and a command economy say they
    cost nothing, and a dollarised country shows Foreign money's minting penalty.
23. **The Budget words.** "N used" names the total and sends the player to Active Policies; "N free" explains that an
    Enable button needs its cost to fit in the free points. The numbers equal the cell's.

## Inflation's reach: the deficit cap and the 60% dial (2026-10-20, #1084)

The bond-finance deficit term is capped at 1.5 points (3 at war) and is 0 while a country is dollarised or in default;
a dollarised country's prices are pulled to the 2% anchor, not to 0. The free dial (fiat, digital, suspended gold)
reaches 60, the rate drifts a sixth of the distance a month and never less than a third of a point, and the stance
term in the inflation sum has its own tight clamp of 10. No engine fact here is new to the mod (`in_default` is read in
several places, and every value is ordinary script-value arithmetic), so there is no self-check line. Read them with
the console event `te_debug_monetary.1` on the country in question.

24. **The late-game count-median falls.** In a save past 2040, count live tags with inflation at or above 50%. Before,
    about a third of tags (31–36) sat there and the count-median was 21–31%; expect a handful at most, the median near
    the 2–4% the big economies run. A tag in the hyperinflation band now should owe it to monetisation, cost-push or a
    trap of its own, not to its deficit.
25. **A dollarised or defaulting microstate prints Deficit 0.** `te_debug_monetary.1` on a bankrupt microstate (Brunei
    or Kandahar in the 2058 autosave) shows `Deficit % of GDP` in the hundreds and `Deficit:` 0 in the pressure line.
    A dollarised one settles near 2% plus half its other pressure (2–3% is typical), not 1% plus half.
26. **A trapped giant gets out without a currency reform.** A fiat AI at 30% or more (China in the 2058 autosave) has
    a target above 25 within a month or two, and its rate climbs several points a month toward it. The simulator, from
    China's 2048 state, puts inflation under 30% in about two years, under 20% in about eight and under 10% in about
    fifteen, with no hyperinflation crisis; a deep recession on the way is expected (real rates in double digits).
27. **The tooltips read the new drift.** The Policy Rate and Rate Target tooltips say the rate closes 17% of its
    distance a month, or of how far inflation is from its target if that is less, and never less than 0.33 of a
    point (33% and 0.67 under Digital Currency), and the delegated mandate's read-out line says the same. The Rate Target tooltip's range reads 0% to 60% (−3% to 60% digital, 0% to
    15% on gold). Shift-click on the stepper goes to 60.
28. **Overshooting the target gains nothing with inflation on target** (fixed in review, PR #1086). With inflation
    near 2%, shift-click a manual target to 60 for a month: the rate moves 0.33 of a point, as it would toward any
    target. With inflation well off target it moves up to a sixth of how far inflation is off, never of the 60.
29. **Wealth Concentration's r > g.** The real rate it reads should now spread both ways: in the 2057 autosave 72 of
    91 countries sat at its −5 floor; at 3–4% inflation the investigation expected about 47 at −5 and 34 at +5.

## A scare is shown once in two years (2026-10-22)

The owner's call: "if a spread happens and it does not trigger a crash, do not fire the relevant event unless it has
been at least 2 years since the last time it fired." The crash-or-scare roll moved out of the popup's `immediate`, which
is too late to hold a popup back, into a hidden event (`minor_events_timelineextended.9`) that the spread now sends six
days out. It sends the popup a day later, so it still lands a week after the reach, for a crash, and for a scare the
country has not been shown in 730 days
(`banking_contagion_scare_cooldown`, set when the scare is sent). A scare inside the cooldown ends there: no popup, no
cycle drop, no radicals. Every engine fact it rests on is used elsewhere in the mod (a hidden event, a delayed
`trigger_event`, a timed country variable, saved scopes riding into a triggered event), so there is no self-check line.

30. **One scare popup in two years.** In a long game, a country the player runs that is reached by several spreads
    that roll scares gets "Contagion from Abroad" (or "Financial Contagion" after a severe crash) at most once in 730 days.
    `save_country_probe.py --var '^banking_contagion_'` shows `banking_contagion_scare_cooldown` after the first.
    *Fallback if a second one still opens inside the window:* the variable is not surviving, or `banking_contagion_decide`
    is not the one sending the popup; look for `minor_events_timelineextended.7` in a `trigger_event` anywhere else.
31. **A held-back scare leaves nothing behind.** After a spread whose scare is held back, the country shows
    `banking_crisis_wave_scared` and `banking_crisis_wave_hit` but no `banking_contagion_pending`, `contagion_crash` or
    `banking_contagion_turned_away`, and its cycle value is unchanged by it. The next wave can reach it again.
32. **A crash is never held back.** A contagion crash inside the cooldown still opens its popup, and does not move the
    cooldown's date. *Watch the title:* the popup is queued after the roll now, with `contagion_crashed` already
    saved, so a crash should open as "Cascading Financial Collapse". If it reads "Financial Contagion" or "Contagion
    from Abroad" instead, the engine takes the title it reads at queue time from before that save
    (`scripting_best_practices.md`, "An event's `title` is read when `trigger_event` queues it"); the options and
    text below it still follow the crash, so that is cosmetic.
33. **The text still follows the origin's severity.** The popup now has a hidden event before it, so the saved scope
    for the crash that started the wave (`banking_crash_origin_country`) rides two delayed hops. After a systemic
    crash (severity 80+), a reached country's popup should read the "systemic" description, and "panic" at 60+, not
    the plain one. *Fallback if it reads the plain text, with `Failed to resolve scope` lines in `error.log`:* save
    the scope again in `banking_contagion_decide` before it sends the popup, as the spread does.
34. **The Great Depression still counts the survivors.** A country that held back a scare reads the survivor text in
    `minor_events_timelineextended.8` (`banking_crisis_wave_scared`) like one that was shown it.
