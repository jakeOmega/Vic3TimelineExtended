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
| `TE_SELF_CHECK … banking_entry_everywhere` | Once a game, 30 days after the first yearly pulse (an old save's first after this change) | every country that should hold `je_banking_cycle` (under the rule, not decentralized, not a rebel) does, and the safety net added none: the engine activated every record | `missing=` countries still without it (each named on a `TE_SELF_CHECK INFO … missing:` line after it, `record=inactive` for one holding an inactive copy the engine has yet to activate, `record=none` for one with no record), `added_by_net=` how many the net has added (each logged as `TE_BANKING: the safety net added …`). The engine left records out (or, for `missing`, a country formed in the last two weeks); the net carries them, a month late at most. The net adds only where there is no record: over an inactive copy `add_journal_entry` is refused with an error, so it leaves that copy to the engine (#1416). **Read BROKEN `missing=3 added_by_net=0` on August 4, 2045 in the owner's EU game (2026-10-17), so the fallback below is in: the net runs monthly** | ~~Add the entry from a monthly pulse instead of the yearly one (`te_banking_entry_net` in `te_banking_entry_on_actions.txt`), so a country waits a month at most~~ (done 2026-10-17). Next: a `TE_BANKING: the safety net added` line for each named country within a month says the net carries them. A `record=none` country the net never adds, while still named a month on, means `add_journal_entry` fails for it: read its type and status in a save. A `record=inactive` country still named a month on holds a copy the engine does not activate though `is_shown_when_inactive` holds (`possible` is `always = yes`): read the copy in a save |
| `TE_SELF_CHECK … mon_union_issuer` | Once a game, on the second monthly pulse of the first bloc leader at Monetary Union tier II or above that can issue a currency (fiat or digital money, a policy rate of its own) and has an adopter worth at least 1% of its own GDP. The 1% keeps out a union too small to pay anything; the second pulse, because a modifier added in one block is not visible to it. A leader that stops qualifying after its first pulse (its adopter leaves) starts again from a first pulse when it next qualifies | the leader's discovery counted its adopters and summed their GDP, its seigniorage and its risk-premium cut are above zero, and Common Currency, Seigniorage from the Common Currency and Issuer of the Common Currency are on its banking entry. The line gives `adopters`, `adopter_gdp_m`, `seigniorage` (pounds a week), `cut` (points), `points` and `credit` **Read OK on February 10, 1982 in the owner's USA game (2026-11-19, 1.15.2): `country=USA adopters=11 adopter_gdp_m=1302.8 seigniorage=1482676 cut=0.112 points=2 credit=0`** | a sum is zero or a modifier is missing; the line gives the same figures | `adopters` or `adopter_gdp_m` at 0: the discovery's sum, read across scopes in an op slot, failed. In `te_monetary_discover_union` write the member's GDP into its `te_mon_work_gdp_m` and add `prev.var:te_mon_work_gdp_m` inside `root = { }`, as the global anchored-GDP pass does. Both above 0 and `seigniorage` or `cut` at 0: `te_mon_union_reach`'s nested `divide = { }`; compute the denominator into a variable in the effect and divide by it. All four above 0: a scaled modifier did not land on the entry; read which is missing, and apply the three on the country instead. **No line** in a game where a leader's Monetary Union row shows such an adopter: the walk of the bloc's members never holds; use the stored count (`var:te_mon_union_adopters >= 1`) in `te_mon_union_is_issuer` |
| `TE_SELF_CHECK … cw_sob_survives_build` | Once a game, a week after `banking_law_cascade_on_uprising` (`extra_effects.txt`) enacted State-Owned Banking for an uprising that came out of its build with Command Economy and no State-Owned Banking (its `TE_BANKING: the uprising … enacting it` line); no verdict if the uprising has left Command Economy by then | the law enacted at `on_revolution_start` held: the hook runs after the engine's last copy of the origin's laws, as vanilla's own `on_revolution_start` assumes when it reads the uprising's Single-Party State | the uprising holds Command Economy and another banking law, so the engine copied the origin's Financial Regulation in after `on_revolution_start` as well, and this write is lost too | Enact it a day later: `trigger_event` a hidden event on the uprising with `days = 1` whose `immediate` runs the same test and `activate_law` |

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
7. **The text matches the options.** A country whose own roll crashed reads "Their Crash Becomes Ours" and the
   cascade description and sees the crash-only options where its laws and institutions allow; a scare reads
   "Contagion from Abroad" (or "Panic Abroad" after a severe crash) and gets only "Close the gates" and
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
    within the year gets "Contagion from Abroad" (or "Panic Abroad" after a severe crash) with only "Close the
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
`[GetStaticModifier('x').GetDesc]` inside a key that `GetCustom` returns, and a word's own tooltip inside a cell that
has one. Since 2026-10-30 the words are not underlined (`gui_style_guide.md` rule 3), as vanilla's readings aren't.

19. **Each word is hoverable.** Six cells: Cycle Phase, Momentum, Bubble Pressure, Budget (the used line and the free
    line separately), Policy Stance (needs a dial) and Inflation (full Banking System). Each word keeps its color (green
    Expansion, red Panic) with no underline. Hovering the word shows its own tooltip; hovering the caption or the icon
    still shows the cell's.
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
29. **Dynastic Wealth's r > g.** The real rate it reads should now spread both ways: in the 2057 autosave 72 of
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
    that roll scares gets "Contagion from Abroad" (or "Panic Abroad" after a severe crash) at most once in 730 days.
    `save_country_probe.py --var '^banking_contagion_'` shows `banking_contagion_scare_cooldown` after the first.
    *Fallback if a second one still opens inside the window:* the variable is not surviving, or `banking_contagion_decide`
    is not the one sending the popup; look for `minor_events_timelineextended.7` in a `trigger_event` anywhere else.
31. **A held-back scare leaves nothing behind.** After a spread whose scare is held back, the country shows
    `banking_crisis_wave_scared` and `banking_crisis_wave_hit` but no `banking_contagion_pending`, `contagion_crash` or
    `banking_contagion_turned_away`, and its cycle value is unchanged by it. The next wave can reach it again.
32. **A crash is never held back.** A contagion crash inside the cooldown still opens its popup, and does not move the
    cooldown's date. *Watch the title:* the popup is queued after the roll now, with `contagion_crashed` already
    saved, so a crash should open as "Their Crash Becomes Ours". If it reads "Panic Abroad" or "Contagion
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

## GUI audit wave (2026-10-27, #1203)

The Banking slice of the GUI and localization audit (`docs/audits/gui_audit/banking_budget.md`). Nothing here was
seen in game. No self-check line: every new script piece reuses a pattern the mod already runs (a capital in a variable
list, a weekly counter, display-only static modifiers), and what is new is GUI rendering, which no script can log.

35. **Greyed external tools say why.** With a tool unaffordable or out of season (Emergency Import Financing outside a
    crisis, Sterilization off gold), its Enable tooltip lists phrased conditions with ticks ("A financial
    crisis is under way: …", "Your treasury can pay this month's cost") and no raw names
    (`te_mon_in_financial_crisis`, `banking_external_export_share > 0`), and no always-ticked availability line.
    *Fallback if a bare trigger still prints:* the engine renders a `hidden_trigger` too; wrap it in a
    `custom_tooltip` with a key instead.
36. **Monthly work prints as modifier lines.** The tooltips of Open-Market Operations, Capital Controls
    and the five External & Currency tools show "Each month:" over coloured lines ("Pull of the Rate Gap −75%",
    "Treasury Cost, of Annual GDP +0.01%"); Monetise Deficit's buttons show "Each step, while it runs:" and the mandate
    buttons "for each step looser:" the same way. *Fallback if `GetStaticModifier(...).GetDesc` renders empty in an
    ExecuteTooltip:* print the figures through a `custom_tooltip` key that reads the same display modifier from loc.
37. **The Monetary Policy rows are short, and How Banking Works has the rules.** Hover each row: a reading and its
    breakdown, no paragraph that repeats the label's concept. How Banking Works lists The Mandates, Gold and the Peg,
    The Exchange Rate, International Arrangements and Prices under the monetary topics. Check the mandate buttons'
    own tooltips (each its rule, then the price of a looser one) and the Target row's drift line.
38. **History bars.** A month with a policy change reads "Policy adopted this month:" then the policy's name, one line
    each; no live figures, no Requires line. A Cycle Value bar reads "Banking Cycle Value: Expansion" (the phase
    word in its colour), Banking Momentum and Bubble Pressure their bands. *Fallback if the band word is missing:*
    `AddLocalizationIf` with a nested `And` over `ScriptContainer.GetVariableValue` did not resolve; record a band
    code at sampling (`te_hist_v_bank_*_code`) and switch on it with `SelectLocalization`.
39. **Active Policies names.** A running Bank Holiday reads "Bank Holiday: N days left", falling by about 7 a week
    from 90; other tools read as what is in force ("Raised Reserve Requirements"). "No intervention points free"
    shows above Available Interventions at 0 points, with the breakdown on hover.
40. **Backstops and Monetary Union rows.** With a swap line or guarantee received or extended, each partner shows
    under Backstops with its flag, name and points. A bloc leader with the Monetary Union principle sees each member
    under Monetary Union: flag, name, a status word and its cost. *Unproven GUI facts:* `Scope.GetState` then
    `State.GetCountry` from a datamodel item (the Grand Monuments and covert rows each prove one step), and
    `JournalEntry.GetCountry.GetPowerBloc` as a datacontext over `PowerBloc.GetMembers`. *Fallback if a name or flag
    is blank:* print the rows from a scripted GUI's `ExecuteTooltip` in fixed slots, as the Cultural Hegemony board
    does (`gui_modding_guide.md` gotcha #15).
41. **The two bills are weekly expenses (owner, 2026-10-27).** With Sterilization or Emergency Import
    Financing on, Government Expenses rise by a quarter of the month's cost (the tool's "Weekly cost" line), the
    Breakdown lists it under Banking with the bill modifier in its sources, and the treasury takes no monthly lump.
    Disable the tool, or change economic system: the expense goes the same week. A month the treasury cannot cover
    still lifts the tool. FX Surrender's purchase still lands monthly, and the Banking row's hover names it.
42. **Breakdown.** Rows, amounts and the How notes read at the panel's 17 (subheadings at 20); "Ministry of
    Intelligence and Security" wraps rather than eliding. Hover Income Taxes' amount: the Overview's graph tooltip.
    *Fallback if it renders nothing on a row's amount:* put the `using` on the row, or give the row a tooltip key.
    An institution's hover gives its level and share of the pool; Administration's gives the pool. A banking event
    charge's modifier tooltip reads "Breakdown: Banking" under Government Expenses.

## The investment pool's weekly add before the cycle starts (2026-11-07)

`je_banking_cycle`'s weekly pulse now runs `banking_weekly_investment_pool_add` for every holder of the entry, its
cycle started or not; until then it waited for the cycle. Pick a country without Stock Exchange (the entry shows Not
Started).

1. **Neocolonial Dependency takes from a dormant pool.** Give the country Neocolonial Dependency (free a colonial
   subject under the Neocolonialism law, or `event` the decolonization release). Its investment pool's weekly change
   falls by 12% of the pool's weekly gross income, as it would with the cycle running; before the change it took
   nothing.
2. **The UN grant goes into a dormant pool.** A Development Fund recipient whose laws keep an investment pool: the UN
   panel's Our Obligations line reads "into our investment pool", not "into our treasury", the modifier list shows
   the pool grant (Weekly Investment Pool Change) and not the treasury one, and the pool grows by the grant each week.
   Under laws with no investment pool, or with the Banking System rule Disabled, it still reads "into our treasury".
3. **Nothing else wakes.** The dormant entry still shows no phase, bars or tools, and no banking events fire.

## The rule switched off mid-game (2026-11-08)

A Workshop player set the Banking System rule to Disabled and found the entry, its bonuses and its bubble-pressure
events still running. Start a game with banking Enabled, play until a country's cycle runs (Stock Exchange and a
level 5 Urban Center), use a tool, then set the rule to Disabled from the screen that changes country.

1. **The entry closes.** Within a week the Banking Cycle entry leaves the journal, and the modifier list shows no
   phase, bubble-inertia, stance-band or tool modifier.
2. **Nothing wakes.** No banking event fires, no "banking cycle started" notification arrives, and the Budget panel's
   Banking tab shows no running cycle.
3. **Switched back on.** Set the rule to Enabled again: within a month the entry is back, and a country that meets the
   start test begins a fresh cycle at 50 (Stable). If the entry never returns, `add_journal_entry` doesn't re-add a
   type the country concluded: give `te_banking_entry_net` a different route back, or say in the rule's text that
   switching it off is for good.

## Open-Market Operations grows with the shortfall (2026-11-10)

A player's independent Fiat country sat in a Panic for five years with prices falling 10% a year, its rate on 0%,
Open-Market Operations and the expanded deposit guarantee on. Open-Market Operations now adds 1 point of inflation
pressure plus half a point for each point last month's inflation sat under the 2% target, up to 5
(`banking_cycle_simulation.md` §28). Put a Fiat or Digital country with a dial on its floor into deflation (a crash
in a Panic, or `te_debug_monetary` to seed headline).

1. **The row follows inflation.** With Open-Market Operations on, the Asset Purchases tooltip's Open-Market Operations
   line reads 1 + 0.5 × (2 − inflation), between +1% and +5%: about +3% at −2%, +5% at −6% and below. With inflation
   at 2% or above it reads +1%, as before. It changes month to month with inflation, never by more than half a point
   for each point inflation moved.
2. **The card says so.** The Open-Market Operations button and dashboard row show, under *Each month:*, the +1.0%
   line and then "Plus 0.5% for each point Inflation runs below its target, up to 5% in all: 3% with prices 4 points
   under target", with Inflation a working concept link.
3. **A deep fiat deflation ends.** An independent Fiat country on the −10% clamp in a Panic, with Open-Market
   Operations on and the bank's own purchases at +5%: Inflation on the History chart leaves −10% within a few months
   and reaches 0% within about three years, and the cycle leaves the Panic about then. Before the change it stayed
   on the clamp for years.
4. **No overshoot to speak of.** Once inflation passes 2% the programme is back to its +1%. If inflation runs past
   6% after a recovery with the tool still on, note how far: the simulator puts the median peak at 5.5%, against
   5.8% with the flat point.

## Event-sweep follow-ups (#448, #798; listed 2026-11-12)

Two checks carried from #798's test plan. Neither has a vanilla precedent.

1. **`clear_scaled_debt` takes a script value.** In a market economy with debt over a quarter of its credit limit,
   fire `banking_cycle_events.10` (Sovereign Debt Scare) and take C, "Default on part of the debt". The debt falls by
   a quarter, and neither `error.log` nor `debug.log` mentions `clear_scaled_debt`. The sovereign debt crisis's
   write-offs (`banking_debt_effects.txt`, reprofiling and the deep haircut) rest on the same answer. If the debt
   does not move, the effect takes only a literal: fall back to a few `scaled_debt` bands with a literal each.
2. **The peg tooltips follow the controls.** Fire `event te_peg.1` on a gold-standard country with a national bank
   whose cycle has not started (no Stock Exchange or no level 5 Urban Center), and hover each option: the texts
   name what its read-only readout shows (Peg Confidence, the Exchange Rate Index) but no control: Defend reads
   "your central bank holds its rate", not "your rate target" (the `.no_je_tt` versions). On a country whose cycle
   runs, the options name the dial (the `.tt` versions). Since 2026-10-17 every country holds the entry, so the
   switch is `te_banking_controls_open`, not the entry.

## The arrangement events, one namespace to a file (2026-11-12, #1403)

`events/te_monetary_arrangement_events.txt` declared two namespaces, `te_lolr` and then `te_union`; the `te_union`
events now have their own file, `events/te_monetary_union_events.txt`. Nobody has established what the engine did
with the second `namespace` line, and none of these four events has been seen in a running game. If the old file
was dropping one namespace's events, they fire for the first time with this change, so each needs seeing once. The
only earlier mention of The Question, P5-17 in `monetary_policy_design.md` ("fewer than ~6 times a campaign"), passes
if it never fires.

1. **The Question of the Common Currency (`te_union.1`) fires at least once.** As a member of a bloc whose leader
   runs a common currency at Monetary Union tier II or above, hold out; have the leader Press for Convergence (play
   the leader in a second game, or wait for an AI leader to). The event opens on the pressed human holdout within
   the month, names the leader, and Adopt and Refuse each do what their tooltips say. If it never opens:
   `error.log` for `te_union`, then `te_monetary_update_union`'s step 9b.
2. **Out of the Common Currency (`te_union.2`)** has its row in the Events table of
   `told-of-effects-playtest.md`; run it in the same game.
3. **The Guarantee Is Called (`te_lolr.1`) fires on the guarantor.** Sign a Lender of Last Resort treaty as the
   guarantor of a country that then defaults (P5-9 has the rest: once in five years, and what reneging does). The
   event opens on the guarantor when the ward defaults and names the ward.
4. **The ward is told (`te_lolr.2`).** As the ward in the same arrangement, default: the event opens once the
   guarantor has answered, with the honored text and the sum when it pays and the refused text when it does not.
5. **The log.** After a game in which the above ran, neither `error.log` nor `debug.log` has a line naming
   `te_monetary_arrangement_events.txt` or `te_monetary_union_events.txt`.

## A common currency pays its issuer (2026-11-14)

The leader of a bloc whose common currency a member has adopted now carries what its adopters carry, mints a share of
its own GDP and has risk premium cut in proportion to its currency's reach, holds up to four more intervention points,
and shares a common capital market with its adopters (`monetary_policy_design.md` § 0.14). The script is run offline
by `test_monetary_union_leader.py` and `test_banking_overdraft_shed.py`; these are what only the game shows. Play a
bloc leader on Fiat Money with a national bank, take Monetary Union to tier II or above, and get a member to adopt
(Press for Convergence, or an AI minor inside your market). Read `TE_SELF_CHECK mon_union_issuer` (the table above).

1. **The principle's tooltip.** A script-only numeric type prints in a principle's `leader_modifier`: the owner's
   screenshot of Monetary Union V (2026-11-15) showed the leader's figures. Since then (owner: the lines read as
   paragraphs) the names are short labels. Tiers II to V show a Leader block of three lines, "+0.50% Common Currency
   Seigniorage", "−0.50% Issuer Risk Premium" and "+1 Issuer Intervention Budget" at tier II, rising to +1.50%, −1.50%
   and +3 at tier V, each green. Under Non-leader Bloc Members, tier I shows "−0.50% Swap Line Risk Premium" and "+1
   Swap Line Peg Confidence a Month", and tier V adds "−50% Adopters' Overvaluation Risk Premium" and "−0.25%
   Adopters' Credit Standing". Tier I has no Power Bloc block; tier V's has four checkmarks (Members May Adopt the
   Common Currency, Leader Is Lender of Last Resort to Adopters, Common Currency Banking Union, Common Currency Is a
   Reserve Currency), +2 cohesion per member, +10% Common Currency Trade Advantage, +5% Common Currency Investment Pool
   Contribution, −25% Common Currency Banking Crash Likelihood, −25% Common Currency Banking Cycle Volatility and +1
   Common Currency Intervention Budget, each green. "Common Currency" and "Currency Reach" link their concepts. A
   figure missing, or a raw `power_bloc_te_mon_…` key: a script-only numeric type does not print in a principle's
   `power_bloc_modifier`; the fallback is to move those lines to `member_modifier` as `country_` types.
2. **The entry's modifiers, the month after a member adopts.** The leader's banking entry lists Common Currency
   (+5% export and import advantage), Seigniorage from the Common Currency (pounds a week), Issuer of the Common
   Currency (a negative risk premium), Central Bank of the Union (+1 to +3) and Common Capital Market. From tier IV
   also Banking Union, from tier V Reserve Currency. Hover the Monetary Union row: the tooltip ends with the number
   of adopters and the reach as a percentage, and for a leader that is being paid, its seigniorage in pounds a week
   twice: before its bonuses to minting, and with them.
3. **The figures.** The Seigniorage from the Common Currency modifier carries the tier's percentage of the leader's
   GDP × reach ÷ 52 (the overview's GDP; at tier V and a reach of 28%, 0.42% of GDP a year). **That is before the
   leader's minting bonuses**: the budget's minting line rises by it × (1 + the bonus), 1.6 times on Fiat Money
   with the five finance technologies and 1.75 on Digital Currency (the budget's minting tooltip lists the
   bonuses). Check three things. (a) The line rises by the multiplied figure, as the 1957 save's did for the old
   seigniorage. (b) The row tooltip's first figure is the modifier's. (c) Its second figure is the first × (1 + the
   bonus the budget shows). **If the two figures are equal while the budget shows a bonus**,
   `modifier:country_minting_mult` reads nothing from a display script value: take the second figure out of
   `banking_dash_mon_union_issuer_note_paid` and leave "before its bonuses to minting", or build the bonus in
   script from the law and the five technologies. The risk premium on the dashboard falls by the tier's points ×
   reach, **a month after** the modifier appears.
4. **More tools at once.** The budget cell's total rises by the points. With them, switch on a tool the old budget
   had no room for (under Central Bank Independence at tier III or above: Reserve Requirements, the Countercyclical
   Buffer and Margin Requirements beside a standing Deposit Guarantee).
5. **Losing the points.** With those tools on, lose the points: have the last adopter leave, or enact Unregulated
   Banking. The budget's free figure goes negative that month, and each following month one tool is lifted, the
   cheapest first (Moral Suasion, then a 2-point tool), with its "withdrawn" marker on the history chart and no
   radicals, until the budget is at 0 or above. A Bank Holiday in force is not lifted. Emergency Liquidity, if it is
   the one lifted, pays its refund. **Each lift posts a feed notice, "Intervention Budget Overdrawn"**, naming the
   tool in bold and saying the budget no longer covers the interventions in force; Emergency Liquidity's adds that
   1% of GDP has come back. A raw `banking_…` key or "an intervention" in place of the name: the flag variable the
   notice reads (`banking_overdraft_lifted`) is not being compared as `flag:<modifier>`; the fallback is one notice
   per tool family with no name. After two lifts in successive months, open the first notice again: if it now names
   the second tool, the feed draws its text afresh from the variable, and the name has to be stored per notice (a
   saved scope cannot carry a modifier; one message type per tool can).
6. **A law downgrade sheds too.** With no union at all: under Prudential Banking switch on the Deposit Guarantee and
   two leaning tools, then enact Universal Banking, Light Prudence. Before this change the tools stayed on an
   overdrawn budget; now they are lifted one a month as in 5. The same for a command economy's planning tools and a
   cooperative's council tools after a law that cuts the budget. **And only what the budget needs.** Under Directed
   Credit & Development Banks with a national bank (6 points, two sectors) run Agriculture credit, Infrastructure
   credit and Moral Suasion, then enact Universal Banking, Light Prudence (5 points, one sector). The first month
   lifts Agriculture credit alone (the sector cap) and the budget is +1; Moral Suasion must still be on a month
   later. Likewise under Prudential Banking with Outflow Controls, the Deposit Guarantee and Moral Suasion: after
   Universal Banking the controls go and nothing else. If Moral Suasion goes in the same month, the mark the
   earlier step sets (`banking_overdraft_wait`) is not seen by the chain: move the chain to its own on_action a
   day later.
7. **The adopter's side.** An adopter's entry lists Common Capital Market, with "+2%" capitalists' investment pool
   contribution at tiers II and III, +3% at IV, +5% at V. The figure is the same in a Downturn or a Panic as in a
   boom, so a slump still takes its whole 10 or 25 points off capitalists' contribution beside it. A country under
   Excess Private Construction has no such modifier.
8. **Unregulated Banking.** A leader under it has neither Central Bank of the Union nor Banking Union, at any tier,
   and keeps the rest. An adopter under it has no Banking Union either (since #1812; "Leftovers of the monetary
   layer" below, check 1).
9. **The last adopter leaves.** Within a month the leader's entry has lost every modifier in 2, and 5 follows if
   tools were running on the points. **At tier V too, with a country still pegged to the leader's money by
   treaty**: the peg counts toward reach only while a member of the bloc has adopted, so seigniorage and the cut
   in risk premium go with the last adopter.
10. **Simplified mid-game.** Switch the banking rule to Simplified: within a month none of the modifiers in 2 is on
    the entry or the country, and the budget is the law's and the bank's alone. The principle's Leader lines still
    print; nothing pays them.
11. **The AI.** In an observer game, count the blocs whose leader is on Fiat Money or Digital Currency with a
    national bank and that hold a Monetary Union principle, against none before. A leader on gold should not take
    tier II. Leaders at tier III should go on to IV and V when the technologies land (T-10 in § 0.11).
12. **Is it strong enough?** The owner judged the strength "about right - good enough to test in-game at least"
    (2026-11-14). Lead a union for a decade and compare it with the group you gave up for it. **If it tests weak,
    the levers are more seigniorage, more trade advantage or another intervention point, never relief from the
    cycle's penalties**: the owner had a doubling of the pool bonus in a Downturn or Panic removed because "the
    investment pool contribution decrease is the worst part of downturns and panics. I worry this would make them
    less painful and so make you not need to avoid them as much." A downturn or a panic should hurt a union's
    leader and its adopters as much as anyone.
13. **A tool that is on more than once.** The owner's 1957 save has Moral Suasion on Singapore's entry three times,
    holding 3 points (issue #1811: the dashboard's Enable tests "not already on" where it is shown, not where it is
    valid). Overdraw that budget by 1 and watch the first lift: if the budget's free figure rises by 1, one
    `remove_modifier` takes one copy, and a stack of three is three months and three notices; if it rises by 3, it
    takes them all and the chain lifted more than it needed. Either way the chain's branch stays true until the
    last copy is gone, so no other tool goes first.
14. **The capital market and Excess Private Construction, year on year.** The Common Capital Market's pool
    contribution is withheld under Excess Private Construction, which is measured once a year. On an adopter whose
    pool is close to what its private queue can spend, the contribution can itself tip the pool over: Excess
    Private Construction appears, the contribution goes the next month, pool income falls, the yearly check drops
    Excess Private Construction, and the contribution returns. Watch an adopter's banking entry for Common Capital
    Market coming and going every year or two beside Excess Private Construction doing the opposite. Singapore is
    the only country under Excess Private Construction in the three saves read, so no size for a band could be
    taken from them. If it flips, hold the contribution off while `too_much_private_construction_last` is set (the
    five years after an episode ends, which the construction system already keeps) by adding that test to
    `te_mon_union_pool_is_saturated`.
15. **A month when something else lifts a tool.** Let Emergency Liquidity wind down (twelve months at Stable or
    above) on an overdrawn budget: the wind-down's own notice appears, the refund is paid once, and the overdraft
    notice does not appear until the month after, if the budget is still short.

## Five timed monetary modifiers survive a revolution (2026-11-12, #470)

A revolution's winner inherits no modifier, so a rebel win used to clear the Break the Peg premium
(`te_mon_peg_broken_premium`), Devalue's inflation pressure (`te_mon_peg_devaluation_pressure`), a currency reform's
premium (`te_mon_currency_reform_premium`), the bloc-currency exit premium (`te_mon_union_exit_premium`) and a holdout's
`te_mon_union_independence`. Each now has a `te_mon_*_months` counter, set where the modifier is added and ticked down by
`te_mon_cw_tick_penalty_clocks` each month, and `te_monetary_inherit_central_bank` re-adds it from that counter. The two
decaying ones come back at the share of their term left, read off a ladder of literal months and multipliers
(`te_mon_cw_restore_decaying_24` / `_120`), as `cr_rebuild_outcome_modifier` rebuilds the civil-rights outcome modifiers.

1. **Each comes back.** In a game where a country holding one of these loses a revolution to its rebels (the console's
   `te_debug_monetary` options or a save with a revolution about to end), compare a save before and just after the win
   with `save_country_probe.py --diff <before> <after> --tag <TAG> --var '^te_mon_.*_months$'`. The winner holds each
   counter at the loser's value, and the modifier is on the winner with roughly that many months left (within three
   months above six). If it is missing: `te_mon_cw_restore_timed` / `_decaying` in `te_monetary_civil_war_effects.txt`.
2. **A decaying one resumes where it was.** A devaluation a year old (12 of 24 months left) or an exit five years old:
   the winner's modifier tooltip shows about half the full value (+1.5pp inflation pressure; about +1.5pp premium), not
   the full value. Full value or near 0: a literal `multiplier` on an `is_decaying` add is not read as a starting
   strength; read `cr_rebuild_outcome_modifier`'s civil-rights modifiers on the same winner, which rest on the same
   reading.

## Every intervention costs a little to switch, and the same (2026-11-14)

The owner's rule: switching any intervention on and off again costs something, Moral Suasion and the other economies'
three 1-point tools excepted, and the routine tools all net the same small round trip, 0.5% of pops radicalized
(`banking_toggle_radicals_value`) or 0.2% of GDP for the lending tools (`banking_toggle_treasury_cost`), paid on
switching on. `test_banking_toggle_costs.py` holds the script to it; these are what only the game shows.

1. **The figure reads 0.5%.** The engine prints `add_radicals` with one decimal (`$VALUE|-=1%$`). Hover Enable on
   Raise Margin Requirements or Restrict Speculative Inflows: "0.5% of Pops become more Radical", not 0% or 1%. Lift
   it: nothing is charged. Withdraw an Expanded Deposit Guarantee: "2.5% of Pops become more Radical".
2. **The radicals land.** Note a state's radical count (its pops panel), raise margin requirements, and read it again
   next day: up by about half a percent of the state's pops. Nothing at all: a fraction this small is lost in the
   engine's rounding, so the friction needs a larger value (1%, vanilla's `very_small_radicals`).
3. **The lending tools charge 0.2%.** Enable Open-Market Operations or a directed-credit sector: the tooltip and the
   treasury both show about 0.2% of GDP (the overview's GDP × 0.002), and lifting it charges nothing.
4. **The council tools.** Under Cooperative Ownership, Dividend Restraint Resolution radicalizes 2.5% of the middle
   strata when switched on and turns 2% loyalist when lifted, every time (no five-year wait any more), and Mutual Aid
   Fund Deployment the other way round for the lower strata.

## External & Currency: one promise each, on every currency (2026-11-14, PR 1)

The five exchange tools' tooltips gained an "On this currency" line under the description, picked by the country's
currency (`banking_ext_now_*` in `banking_dash_custom_loc.txt`) and printing live figures (`banking_ext_disp_*` in
`banking_external_values.txt`). Capital Controls (Outflows) is now Capital Controls and Sterilize Capital Inflows is
Sterilization. Nothing a pulse runs changed. Design: `docs/superpowers/archive/specs/2026-11-14-external-currency-tools-design.md`.

1. **The line renders, on each currency.** Hover each of the five rows (Enable and active) as a country on a convertible
   Gold Standard with a national bank, as one on Fiat Money with a national bank, and as one on Commodity Money. Each
   tooltip shows "On this currency:" between the description and "Requires:", with figures, not raw `[...]` calls or
   keys. Gold: Capital Controls and Restrict Speculative Inflows give the World Rate Gap, and it matches the dashboard's
   World Rate Gap row while controls are off (a quarter of it while on). Fiat: the two give the rate term, and with
   neither tool on their first figure matches "The real rate against the world's" in the Exchange Rate tooltip. Commodity Money: both
   say nothing moves. *If a line is blank:* the custom loc's trigger fails in the tooltip's scope; check that
   `[Country.GetCustom('te_mon_fx_controls_note')]` renders in the Exchange Rate tooltip, which uses the same scope.
2. **Sterilization's figures.** On gold with gold arriving (a policy rate above the World Rate), Sterilization's line
   gives two price-pressure figures, the second a quarter of the first; with the rate below the world's it says no gold
   is coming in.
3. **Limit Foreign-Currency Borrowing below par.** On Fiat Money with the index below 100, the line gives the points
   below par, the premium they add (0.05 a point) and what is left after protection; with the limits on for a year the
   second figure is about three quarters of the first. On gold it says the currency stays at par.
4. **The new names.** Capital Controls' row, its End button and the modifier on the entry read "Capital Controls";
   Sterilization's read "Sterilization" and its weekly bill "Sterilization Bill"; an option of
   `minor_events_timelineextended.7` adds "Targeted Capital Controls".

## External & Currency: Sterilization and surrender on a floating currency (2026-11-14, PR 2)

Sterilization halves how fast a floating index moves toward its target (`banking_external_fx_adjust_factor` in
`te_mon_fx_shadow_step`); the surrender requirement adds up to 4 points to a floating target
(`banking_external_surrender_fx_term`); Restrict Speculative Inflows, Sterilization and the surrender requirement need
gold flows or a floating currency with a national bank; Limit Foreign-Currency Borrowing is hidden on metal at par.
The script scenarios in `test_banking_external_tools.py` run each formula; what follows only the game shows.

1. **Sterilization slows the index.** On Fiat Money with a national bank and the index well away from its target
   (the Exchange Rate tooltip's "Where it is heading" ten points or more from the index), note the index for two
   months, enable Sterilization, and note two more: each monthly move is about half the one before it would have
   been, the tooltip's first lines carry "Sterilization: the index closes a twenty-fourth of the distance a month",
   and the tool's "On this currency" figures are the move now and half of it. The weekly bill shows under Banking in
   the budget. *If the index moves as fast as before:* the funded flag is unset when step 5b reads it; check
   `banking_external_monthly_update` runs before `te_monetary_update_fx` in the monthly update.
2. **Surrender lifts the target.** On Fiat Money with exports, enable the surrender requirement: the Exchange Rate
   tooltip gains "Exporters' earnings sold to the central bank: +4.0" (+2.0 or +1.0 with fewer exports) and "Where
   it is heading" rises by as much; the treasury pays nothing and the Banking row in the budget names no purchase.
3. **The shared requirement.** On Commodity Money with a national bank, the three flow tools' Enable rows are
   greyed with "Your country's national bank sets its own rate, on the gold standard or a floating currency"
   unticked, and an active Restrict Speculative Inflows is lifted the month after the switch, with its history mark.
   Suspending convertibility on gold with Sterilization on leaves it on, and its line turns to the floating one.
4. **Limit Foreign-Currency Borrowing at par.** On a convertible Gold Standard its Enable row is gone from Available
   Interventions; after a devaluation (index 88) it is back, and it is lifted again the month the index returns to
   par. On Fiat Money it is there as before.

## An adopter's inflation follows its leader's (2026-11-15)

A common-currency adopter's core inflation is pulled toward its leader's by a point of pressure for each point between
them (`monetary_policy_design.md` § 0.15). `test_monetary_union_price_pull.py` runs the branch and step 6 offline;
these are what only the game shows. Play a bloc at Monetary Union tier II or above with a member that has adopted.
Core inflation is hidden, so read it with the console event `te_debug_monetary.1`, on the adopter and on the leader.

1. **The copy reads the leader's core.** The adopter's regime-pull line in `te_debug_monetary.1` equals the leader's
   core less the adopter's, to the decimal, give or take the month the leader's own pulse moved it. *If it reads the
   adopter's own core negated (the leader's figure as 0) or the seed's 2 for good:* `scope:te_mon_anchor_now.var:
   te_inflation_core` is not read across countries in step 1c, the same read as the rate copy in P5-1.
2. **The gap narrows.** Over three years after adopting, an adopter that joined 2 to 3 points above its leader comes
   within about a point and a half, its own pressures permitting, and its Price Band follows. A treaty pegger and a
   currency-board subject keep their own inflation as before.

## Leftovers of the monetary layer (2026-11-15, #1812)

Five things left over from the Monetary Union's leader benefits (`monetary_policy_design.md` § 0.16). The script and
the texts are held offline by `test_monetary_union_leader.py` (`RegulatorTest`, `OtherMintingFiguresTest`) and, for
the reserve currency's cut at the floor (checks 9 and 10, added 2026-11-16), `test_monetary_reserve_floor.py`; these
are what only the game shows. No self-check: the change rests on no engine fact the mod does not already use the same
way (a law test in a scripted trigger; a scripted trigger in a custom localization's `trigger`).

1. **An adopter under Unregulated Banking is outside the banking union.** In a bloc at Monetary Union tier IV or V,
   find an adopter under Unregulated Banking (in the owner's 1958 Singapore save: ACE, E94, F11, SIA and five more).
   Its banking entry has Common Currency and Common Capital Market and **no Banking Union**; its budget's total is the
   law's 1, and the national bank's 1 where it still has one. An adopter under any other banking law still has Banking Union.
2. **Loading a game from before the change.** Within a month every such adopter loses Banking Union. One whose
   tools then hold more points than its budget has (a Bail-in Regime, Infrastructure or Armaments credit or Emergency
   Import Financing, 3 points each, on a budget of 2) is overdrawn, and a tool is lifted the month after, as in "A common currency pays its issuer",
   check 5. For the player's own country the "Intervention Budget Overdrawn" notice names the tool; the AI is told
   nothing. If a tool stays on an overdrawn budget for more than two months, the overdraft chain is not reaching it.
3. **The row says why.** Hover the Monetary Union row of a country that is in the currency at tier IV or V under
   Unregulated Banking, as that country or as an observer: the tooltip ends, after a divider, with "Outside the
   banking union." in bold and one sentence naming Unregulated Banking. A country under another banking law, a
   holdout, and any country in a bloc below tier IV show no such line. A leader that is also the issuer reads its
   issuer's note first and this one after it.
4. **The principle's tooltip.** On Monetary Union IV and V, hover "Common Currency Intervention Budget", "Common
   Currency Banking Crash Likelihood", "Common Currency Banking Cycle Volatility" and the Banking Union checkmark:
   each names Unregulated Banking as the exception for every country using the currency, not for the leader alone.
5. **Trade advantage: one line or two (ruling G9; the owner's switch waits on this look, ruling L19).** The adopter's Common Currency modifier carries "+5% Trade
   Advantage for Exports" and "+5% Trade Advantage for Imports"; the design asked for one "+5% Trade Advantage". To
   decide the switch, open a trade center's advantage breakdown for an export and for an import in two countries: an
   adopter, and a country in a bloc with External Trade (which gives the overall "Trade Advantage" +25%). If the
   overall figure appears in both the export and the import breakdown, in the same list as the directional ones and
   added the same way, the two forms are the same benefit and the switch is safe (G9 lists what it touches). If the
   overall figure is applied apart from them, or to one direction only, keep the pair.
6. **Monetizing the Deficit says "before minting bonuses".** With Monetize Deficit at 1 or more, the step's tooltip
   line "Money Created a Year, of GDP" and the Monetizing the Deficit modifier each say the figure is before the
   country's bonuses to Minting, with Minting linked. Check the budget: the minting line rises by the modifier's
   figure times (1 + the bonus the minting tooltip lists), not by the figure itself. The step's description ends
   its sentence on the bonuses "and less while your Price Band is Very high or Hyperinflation", with the row's own
   short band names.
7. **Currency-board seigniorage.** An overlord with a currency-board subject: the Seigniorage from Currency Boards
   modifier's figure is half the subject's minting before the subject's bonuses (for a subject above 200M of GDP
   with no gold, 100,250 a week), and the overlord's minting line rises by that times (1 + the overlord's bonus).
   The subject's own "why" line under its policy rate, and its Currency Board modifier, say half of what it mints
   before its bonuses goes to the overlord.
8. **What an unregulated adopter keeps, and what it can now be offered.** Two consequences nobody chose, for the
   owner to rule on (`monetary_policy_design.md`, ruling L16). A crash in a fellow user of the currency still
   reaches such an adopter less readily at tier IV and V (the contagion damp asks the tier and the shared currency,
   not the modifier), though its row says it is outside the banking union. And it can now be offered the Deposit
   Insurance Debate, which the union's common guarantee used to rule out for it: watch for that event on an
   unregulated adopter with Central Banking, in a Stagnation, Stable or Expansion phase.
9. **A reserve currency on its floor is paid in risk premium (2026-11-16, ruling L17).** Find a plain treaty
   anchor, not a bloc leader issuing a common currency, with countries worth 1% or more of world GDP pegged to its
   money and its credit standing on its floor (in the owner's 1940 New York save: Prussia, 4.97%; in the 1958
   Singapore save: Italy and Indonesia). It has the modifier "Reserve Currency Holdings" (on the Nation tab too), and the
   Risk Premium tooltip lists it, at the cut in points the Monetary Anchor row's tooltip gives as "Credit standing from
   arrangements now" (about 0.1 for Prussia, 0.04 for Italy, 0.03 for Indonesia; the two figures can differ by
   up to 0.05, the step every premium term moves by). That tooltip ends, after a divider, with a sentence saying its
   standing is on its floor and giving the same figure as risk premium. A country above its floor, and an anchor
   whose peggers come to under half a percent of world GDP (America, Great Britain, Brazil in the 1940 save), have no
   such modifier and no such line. `test_monetary_reserve_floor.py` holds the script; this checks the engine's sums
   and the tooltip. **Then the open question, the rate (option C of design § 0.16, left for this look):** is the
   benefit worth having for the anchors it pays? It is a tenth of a point at most in the three saves (0.26% to
   0.55% of their income). Note it in the play-test's findings, and whether an anchor's AI or a player would
   seek pegs for it; raising `te_mon_reserve_currency_per_step` is the lever if not.
10. **A leader is not paid twice.** A bloc leader issuing a common currency, on its floor, with treaty peggers too
    (Singapore in the 1958 save): its Issuer of the Common Currency modifier is there and Reserve Currency Holdings is not,
    because its issuer cut (about 0.39 points) is larger than the reserve cut (about 0.08). Where a leader's reserve
    cut is the larger, it has both, and the two add up to the reserve cut, not more; its Monetary Anchor tooltip
    names the issuer's cut. Singapore's Monetary Anchor tooltip ends, after a divider, with a sentence saying its
    issuer cut already covers what the floor cancels.
11. **Watch: imposed pegs and a tier-V leader's reach (ruling L18).** None of the 31 peg articles in the three saves
    is imposed. If a leader at Monetary Union V is seen imposing pegs to raise its reach (Common Currency Reach on
    its Monetary Union row), note how many and what share of its reach they make: the owner's answer to farming is
    to count imposed pegs at a discount, not to exclude them (`monetary_policy_design.md` § 0.16 item 3). Imposed
    pegs also count toward the reserve cut, so an anchor on its floor is now paid for them too.

## No contagion through a country with no states (2026-11-16, #1871)

The contagion asked `is_market_reachable_for_trade` of a country that had lost its last state, and the game crashed
(1.15.1, RVA `0xd63d38`, an observer run in October 1913). The spread now skips a target that holds no state or no
capital, and a country that holds no state or no market neither rolls the monthly crash nor spreads a crash
(item 5 has the one way such a country can still crash).

1. **No market errors from the contagion.** In an observer run long enough for a country to lose every state while
   its war goes on (its probe or snapshot line reads `states=0`), `error.log` has no `Event target link 'market'
   returned an invalid object` with a `banking_cycle_effects.txt` frame, and the run does not crash at RVA
   `0xd63d38`. Vanilla's own lines of that message for the same country (the Corn Laws, the treaty articles) still
   come; they are registered in `docs/vanilla/vanilla_known_bugs.md`.
2. **If it crashes there anyway.** With these guards in place, the next suspect is vanilla's Goods Transfer article
   (`vanilla_known_bugs.md` § "Latent crashes the mod does not patch"), or a country with states but no capital.
3. **Unverified: a living country in a stateless overlord's market** (#1872's review). `exists = market` passes a
   living origin or target that sits in the market of an overlord with no states, which sends the trigger's route
   check a market with no capital. The crash dump does not cover that case; a crash at the same RVA with such a
   subject in the game would point to it.
4. **Not guarded yet, not known to bite: the rest of the monthly pulse** (#1872's review). Nothing in the script
   stops the banking journal entry's other monthly effects, or `banking_cycle_random_event_effect` and the events it
   sends, for a country with no states; only the crash roll and the contagion are guarded. No read in them is known
   to need a capital or a market. Outside the contagion, the banking files (`je_banking.txt` and the `banking_*`
   effects, triggers, values and events) read a market once, `banking_external_export_share` for the export
   surrender tool, behind `exists = market` and with no route search, and read no capital. This is tidiness unless a
   later change adds such a read.
5. **Not guarded yet, not known to bite: a target that loses its last state after the spread reaches it** (#1872's
   review). The guards are read when the spread picks its targets. A target reached while it held land still gets
   the hidden event .9 six days on and, from it, event .7 a day later: neither event has a trigger, and nothing in
   the script stops them (whether the engine still delivers a queued event to a country with no states is unread).
   Its roll there is `banking_contagion_crash_check`, run by .9, not the monthly roll that #1872 put behind
   `is_country_alive = yes exists = market`, so it can still crash; that roll reads its bubble pressure and the
   origin's severity, not a market. It cannot spread the crash: .7's `after` makes it the origin, and
   `banking_cycle_spread_contagion` turns away an origin with no state or no market. It is still counted: the same
   `after` runs `banking_crisis_wave_increment`, which adds it to the wave's country count toward the Great
   Depression's ten and its GDP to the wave's, and then checks for a Great Depression.

## International Arrangements folds on its own (2026-11-18)

The Monetary Policy section's International Arrangements group, which in a monetary union lists every swap, guarantee
and member row, now has a header of its own that closes it (`banking_dash_subsection_header`, flag
`banking_dash_arrangements_closed`, open by default). It is the `section_header_button` shape the UN, Global Warming
and Nuclear panels already use for a section inside a section, at the block's 460 and in the subheadings' 20.

1. **The header reads as one of the block's groups.** As a bloc leader or member under a Monetary Union principle, the
   header sits where the ruled "International Arrangements" subheading was, inside the block's dark background, its
   left edge in line with the Exchange Rate and What Borrowing Costs subheadings around it; it does not look like the
   next section. Its arrow points open, and the text is not elided.
2. **It closes and opens.** A click hides every row under it (Monetary Anchor, Peg Confidence, Backstops, the partner
   rows, Monetary Union, the member rows and the union buttons), and What Borrowing Costs moves up under the header.
   A second click brings them back. Closing Monetary Policy itself still hides the header with the rest.
3. **Nothing moves for a country with no arrangement.** A country with no anchor, treaty or union shows neither the
   header nor an empty gap between Exchange Rate and What Borrowing Costs.

## The Help's Monetary Union note; the backstop costs what it pays (2026-11-18, #1858, #1864)

The Help popup's Monetary Union note now gives all five tiers, one line each, and what the leader earns. And a tier III
leader no longer pays for the relief on an adopter whose debt a treaty guarantee or a receivership already relieves:
`te_mon_union_cost_to_root` asks `te_mon_has_treaty_debt_relief = no`, as the adopter's side always did. The cost is
run offline by `test_monetary_union_leader.py` (`BackstopCostTest`); these are what only the game shows.

1. **The note's lines.** Open the Banking tab's Help, International Arrangements. The Monetary Union note opens "A power
   bloc's Monetary Union principle has five tiers", then five lines, each starting with a tier's name in bold
   (Monetary Cooperation, Common Currency, Fiscal Backstop, Banking Union, Reserve Currency) and none running into the
   next, then the paragraph on the leader. No raw `$principle_monetary_union_N$`, `$too_much_private_construction$` or
   `$law_unregulated_banking$`; Common Currency and Currency Reach are concept links. If the `\n` breaks do not render
   in a note, join the tiers back into one paragraph as the note had them.
2. **A covered adopter costs only its cooperation (and supervision).** As a tier III or higher leader with an adopter
   that also holds a Lender of Last Resort treaty from a third country (or is under a Debt Receivership), that
   adopter's member row under Monetary Union shows a backing cost without the relief: about the swap-line share, plus
   the supervision at tier IV and up, times its GDP over yours. Its Backstops row shows the relief from the treaty, and
   the union's received figure no relief. End the treaty and, at the next monthly update, the member's cost rises by
   the relief times the GDP ratio.

## An uprising's Command Economy keeps State-Owned Banking (2026-11-19)

The cascade that enacts State-Owned Banking when Command Economy activates (`banking_law_cascade_on_law_activated`)
runs while the engine is still building an uprising's laws, and the engine's later copy of the origin's Financial
Regulation law can overwrite it: Kalat's socialist uprising (1978.10.4) held Command Economy and Kalat's Narrow Banking
three months on. `banking_law_cascade_on_uprising` now enacts it again from the civil-war start hook when the uprising
has a Command Economy its origin lacks.

1. **The uprising holds State-Owned Banking.** At the next revolution whose movement brings Command Economy to a country
   that lacked it, `debug.log` has `TE_BANKING: the uprising … enacting it` (only when the build lost the law), and
   the next autosave's `save_country_probe.py <save> --tag <TAG> --law 'economic_system|financial_regulation'` shows
   the revolutionary copy (`revolutionary?`) at Command Economy and State-Owned Banking. The self-check above reads it
   a week on.
2. **An origin's own Command Economy is left alone.** An uprising of a country already in Command Economy keeps
   whatever banking law it copied (Kaarta's Central Bank Independence, enacted in 1975, is one): no `TE_BANKING: the
   uprising` line for it.

## One copy of a tool, however fast the clicks (2026-11-27, #1811)

A 1957 save held three copies of Moral Suasion on its banking entry, holding 3 intervention points where one holds 1:
a second press passed the tool's gate before the first one showed. Every switch-on of the 38 tools now marks the tool
for a week (`banking_pending_<modifier>`), the tool's `banking_possible_*` refuses while the mark is there, and the
tool's own Disable or a law's lift clears it. `test_banking_tool_roster.OneCopyTests` and
`test_banking_external_tools.OneCopyScenarios` hold the script; these are what only the game shows.

1. **Two quick clicks give one copy.** Paused, click Moral Suasion's Enable twice as fast as you can (and, if the row
   still shows Enable after the first click, a third time). Unpause for a day. The entry's modifiers list Moral
   Suasion once, and the free points fall by 1. If the Enable row is still drawn after a click, its tooltip shows the
   red line "Not switched on in the last 7 days, unless switched off since".
2. **Off and on again is never held up.** Enable Moral Suasion, Disable it, Enable it again, all paused: each click
   works, and one copy is on.
3. **Copies already in a save.** On a save that holds a stacked tool (the 1957 Singapore save: Moral Suasion ×3),
   Disable it once and read the entry's modifiers: if a copy is left, one `remove_modifier` takes one copy, and such
   a save needs a monthly collapse of duplicates (the repair #1811 describes); if none is left, Disable already
   repairs it.
