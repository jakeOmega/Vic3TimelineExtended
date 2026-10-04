# Tax code play-test runbook

The checks that decide whether the legislated tax code works in game, in the order to run
them. The design is `docs/superpowers/specs/2026-09-29-legislated-tax-code-design.md`
(packages 1–5) and `docs/superpowers/specs/2026-10-03-tax-code-ai-and-release-design.md`
(the AI and this release). The mechanics are in `docs/systems/tax_code_schema.md`, and
`docs/testing/tax-code-capability-ledger.md` maps each check to a release scenario (its
"Evidence matrix"). The structural tests only show that the script is wired as designed;
whether the engine does what the design assumes is decided here.

## How to run a check

- **Rule.** Each check names its setting of the Legislated Tax Code game rule: *off*,
  *on* (Tax Code Enabled) or *customs* (Tax Code and Customs Enabled). Game rules are
  chosen in the lobby, so a check that needs *on* needs a new game with the rule set.
  The probe harness (`te_debug_tax*`, checks P05–P16 and the customs probe) refuses to
  arm under the rule: those checks run in a rule-*off* game.
- **Console.** Vic3's console has no `effect` command. Script runs as `event <id>`, on the
  player's country unless the check says to select another first. The tax code's console
  events are in the `te_tax_debug` namespace:

  | Event | Does |
  |---|---|
  | `te_tax_debug.1` | Activates Per-Capita Taxation over the carrier law, to test the re-assert |
  | `te_tax_debug.2` | Runs the AI step's managers and initiative now on the player's country, as if it were an AI country |
  | `te_tax_debug.3` | Logs the AI signals (ratio, debt, reserves, streaks) and the five pre-scores |
  | `te_tax_debug.4` | Sets the deficit streak to the need threshold and clears the AI cooldown |
  | `te_tax_debug.5` | Stores a package raising the wage tax one step from next month, with a 1-month expiry |
  | `te_tax_debug.6` | Makes the next monthly dispatch skip this country, so a package due then is missed |
  | `te_tax_debug.7` | Records an outside change to the wage tax, so a waiting package touching it is held as conflicting |
  | `te_tax_debug.8` | Names the capital's state for regional relief in the enacted code |

- **Logs.** Read `debug.log`, not `error.log`. Every tax-code line starts `TE_TAX`; the
  tags are listed in `docs/systems/tax_code_schema.md`, "Debug lines". Lines from player
  countries are complete; AI countries write one `TE_TAX ai_<verb>` line per action.
- **Saves.** `python3 scripts/analysis/tax_code_save_report.py <save> --country <TAG>`
  prints a country's whole code from a save (text or binary), and
  `--diff <before> <after>` compares two saves group by group. Use it for every check
  that says "save report". **Validate it once first** (part of PT-04): it was built
  before any save held the code, so two save layouts are assumed. On the first rule-on
  save, compare its report with the game for one country. If "carrier amendments" reads
  none while the code's indices are set, the amendment join is wrong; if "native tax
  level" is not medium, the medium-omission rule is wrong. Until it is fixed, read
  the save by hand rather than trust its verdicts.
- **Targeting.** The console's `event` runs on the player's country. The AI checks
  observe AI countries through their `TE_TAX ai_*` lines, and use `te_tax_debug.2` on the
  player's own country to run the same managers by hand.
- **Recording.** Copy the result cells into
  `docs/testing/tax-code-capability-ledger.md`'s evidence matrix: *passed*, *failed*,
  *unclear* or *skipped*, with the date, the game version and the log lines or save names
  that show it.

## First session: highest risk

### PT-01 One sync a day

Rule *on*. Day D: `event te_tax_debug.1` twice.
Expect on D+1 two `TE_TAX post-migration sync` lines (one per `te_tax.4`) and one
`TE_TAX sync_deferred`; on D+2 nothing changes.
The carrier law holds exactly one amendment per tax on D+1 and D+2. Also release a
country on the last day of a month: the release's sync and the 1st's processor share a
tick, and the released country must still hold one amendment per tax.
Serves S3. Result: ___

### PT-02 A script value on the left of a comparison in a scripted GUI

Rule *on*. Introduce a bill and watch the Conditions for Passage.
Expect Pass and its Committed Clout row to flip when the committed share crosses 50%,
the Debate row to flip at 0 days, and (rule *customs*) a customs stepper to gray out at
±3. If Pass never enables, script values on the left of a comparison don't work in a
scripted GUI's context: everything gated that way needs rewriting.
Serves S1. Result: ___

### PT-03 Rule off

Rule *off*, any save; also switch the rule from *on* back to *off* in the lobby.
Expect no Tax Code tab, and Budget's bottom edge unchanged. The tax level, the
consumption "+", tariffs, the goods toggle and the right-click Tax/Untax all work. No
Tax Code journal entry, no country on the Legislated Tax Code law, no `TE_TAX` line in
`debug.log`. The five taxation laws' tooltips show at most one plain line about the rule.
Serves S11. Result: ___

### PT-04 Game start under the rule

Rule *on*, new game.
Expect one `TE_TAX migrated` per country that isn't decentralized and none for a
decentralized one, and no `migration_discrepancy`. Spot-check migrated indices: a
Consumption-Based country at medium has consumption 5; Land-Based at medium land 28 and
consumption 5; Per-Capita at medium wage 4, land 14, head 14, consumption 5. On Jan 2
the Budget's income lines equal Jan 1's. On Feb 1 the log shows `dispatch` and `process`
and collections don't change. `event te_tax.3` twice logs nothing the second time. The
journal entry activates, the tab unlocks, and Open Budget opens the tab.
Serves S11. Result: ___

### PT-05 Native controls are grayed

Rule *on*, then *customs*. Try every native fiscal control, including an add menu opened
before the gate closed.
Expect grayed: the tax level, the consumption "+", the add menu, the goods panel's
toggle, the goods-in-state toggle, the goods tooltip and both right-click menus. Tariff
and subvention buttons are grayed only under *customs*. Note whether the vanilla
tooltips on grayed controls confuse.
Serves S5. Result: ___

### PT-06 A bill end to end

Rule *on*. The design's worked example: a dividend tax of 30% that reverts to 15% in
January; draft 25% from February plus a taxed staple. Draft, introduce, accept an offer,
revise, pass, commence, expire.
Expect collections to change only at commencement; interest group cards to show values;
a revision to release commitments and restart the 30 (or 15) day debate; opposed groups
to lose 3 approval, fading over 180 days; `TE_TAX passed`, never `pass_refused`.
Serves S1, S2. Result: ___

### PT-07 The fiscal record of the 1st

Rule *on*, with a bill under debate. Tip the budget into deficit in the middle of a
month.
Expect the State of the Budget reason unchanged until the 1st. A bureaucracy or budget
promise offered before then reads Maintain.
Serves S6. Result: ___

### PT-08 Revenue estimates

Rule *on*. Review a draft that adds a dividend tax from zero; compare an estimate with
the actual receipts a month after commencement; let a temporary rate expire; accept an
offer.
Expect the estimate lines to print numbers (the `Multiply_CFixedPoint` form), a
zero-rate row to read "No current base — estimate unavailable.", "out of date" after an
expiry or a civil-war repair but not after an offer, and a Poll Taxes range in a
Per-Capita country. One `TE_TAX snapshot` a month plus one per revision.
Serves S4. Result: ___

### PT-09 Held packages

Rule *on*. `event te_tax_debug.5` (a wage-tax package for next month), then
`event te_tax_debug.6` before its month; repeat with a fresh `.5` package and
`event te_tax_debug.7` (an outside change to the wage tax, so the package must change
the wage tax to conflict).
Expect the first held as missed, with Move to Next Month available for three months
(history: rescheduled) and Drop always; the second held as conflicting, with only Drop.
Dropping frees promises bound to it (`obl_released`). If the debate class changes, the
debate clock restarts.
Serves S3. Result: ___

### PT-10 Civil war, both outcomes, release and transfer

Rule *on*. A revolution where each side passes a different wartime bill. Once with the
rebels winning, once with the loyalists, once with a seceder winning. Also release a
country, and cede a state named for regional relief. Save before the outbreak and after
the end, and diff the two saves with the save report.
Expect `uprising_copy` and `adopted`, the winner's code and passed bills only, the
history line "The tax code was restored after a civil war", a sync the next day, and no
drift line for the rebels' first sync. A loser's package never commences. Promises
repaired with their clocks unchanged. No "blocked" customs line the winner never had.
The released country starts with its parent's rates and no packages.
Serves S8, S9. Result: ___

### PT-11 Customs under the rule

Rule *customs*. The capability ledger's "Customs schedule in game" items 1–10: owner and
member at the start, a bill raising a level, the cooldown, a `no_tariffs` treaty, a
junior's setter (console), customs-union entry and exit, AI owners, frame cost,
unreadable goods, layout.
Expect adoption only after 4 failed monthly re-asserts, unreadable goods at the vanilla
default with no retry, `customs_lost` and `customs_gained` on market changes, and a
customs-only bill withdrawn when its market is lost.
Serves S5. Result: ___

### PT-12 Layout

Rule *on*, then *customs*. Long good names, interest group names and stance cells, the
expiry cell with money taxes (Rural Assessment, Head Tax), level cells, year.month dates
(1842.1 against 1842.10).
Expect no elision, a hover on every name, and readable dates; note anything that reads
wrong.
Serves S12. Result: ___

### PT-13 AI countries legislate

Rule *on*. A ten-year observer run, then a played run with an AI neighbour in deficit.
Expect `TE_TAX ai_introduced`, `ai_passed` or `ai_withdrawn` lines from AI countries with
fiscal need, and the rates their code sets changing only on the 1st after an
`ai_passed` (native changes between 1sts are the drift the counters measure). Each
January every AI country writes a `TE_TAX ai_year` line with its drift counters, template
and streaks: record the counters' yearly change per country (owner question 2: does the
native AI keep moving its tax level?) and count the `ai_introduced`, `ai_passed` and
`ai_withdrawn` lines per country per year. A country never logs `ai_no_viable` twice in a
row for the same episode.
Serves S10, S13. Result: ___

### PT-14 Frame time

Rule *customs*. Customs section open with eight groups holding offers; the review's
estimates open; the 1st of the month in a late-game save; the lobby to day 1; and the
AI step's days, the 5th, 12th, 19th and 26th, in a late-game save.
Expect no visible hitch against a rule-*off* run of the same save, and the AI step's
daily cost (`te_tax.8` and `te_tax_ai_*` in the profiler) below the 1st's processor
cost (`te_tax.1`). Profile with the script profiler (below) if there is one.
Serves S12. Result: ___

### PT-15 The probe harness's open items

Rule *off*. P05, P08–P11, P15 and P16 from `docs/testing/tax-code-probes.md` and
`docs/testing/tax-code-probes-extended.md`, and the customs probe, P09b and P09c ("Customs:
lock or carrier" in `docs/testing/tax-code-probes.md`).
Expect each recorded in the capability ledger's row for it. P09b/P09c decide whether
customs switches the native controls off at their source; P16 decides whether an
institution promise can be read as delivered and whether `set_institution_investment_level`
sets a level or a target.
Serves S4, S5, S6. Result: ___

## AI legislation

### PT-16 An AI country in deficit raises a tax

Rule *on*. Watch an AI country with a fixed deficit, income at most 90% of its expenses
and low gold reserves for a year. To see it on your own country instead, put it in
that state, then `event te_tax_debug.4` (sets the deficit streak) and
`event te_tax_debug.2`: the streak is reset on the next 1st if the budget is not in
deficit, and the income and reserves conditions still apply.
Expect, within about 8 months of three deficit 1sts in a row, `TE_TAX ai_introduced
tpl=1` (or `tpl=6`, luxury goods, when the consumption rate is the cheapest tax to raise),
then `ai_accepted` for any offers, then `ai_passed`, and
the new rate collecting from its commencement month. `event te_tax_debug.3` (on your own
country) shows the signals and the five pre-scores.
Serves S10, S13. Result: ___

### PT-17 An AI emergency bill

Rule *on*. An AI country in default, or with debt at half its credit limit.
Expect `ai_introduced tpl=2` without waiting for its quarter, a minor bill (15-day
debate), and `ai_forced` if it lacks the votes but has 35% committed, the override
capacity and the Authority. After an emergency bill passes, the next comes no sooner
than about three months later, once a fiscal record has seen the first; after one is
withdrawn, the country waits the six-month failure cooldown (Ruling 12). One early
attempt can follow a reset of the episode marker (the need ending, a civil war, a
release); note any.
Serves S10, S13. Result: ___

### PT-18 AI offers and the chain cap

Rule *on*. An AI bill with several persuadable groups.
Expect at most three `ai_accepted` lines a month, one a day, and no acceptance once the
committed share is above 50%.
Serves S13. Result: ___

### PT-19 AI withdrawal and no viable bill

Rule *on*. An AI country whose groups oppose any rise, or with legitimacy below 25.
Expect `ai_withdrawn` with a reason, one `ai_no_viable` for the episode, and no new AI
bill for six months. Rebels below 25 legitimacy log `ai_no_viable` once and try again at
most every six months.
Serves S10, S13. Result: ___

### PT-20 AI held packages

Rule *on*. On your own country: `event te_tax_debug.5`, then `.6` (missed) or `.7`
(conflict) before its month; after the month passes, `event te_tax_debug.2`. In an
observer run, watch AI countries' `ai_rescheduled` and `ai_released` lines.
Expect `ai_rescheduled` for a missed package within three months, `ai_released`
otherwise; never both slots held for more than a month.
Serves S13. Result: ___

### PT-21 AI promises

Rule *on*. An AI bill that accepts a Ministry of Education or Ministry of Health promise;
let it run to the deadline.
Expect one `TE_TAX obl_deadline result=met` or `result=unmet` line per promise, for
player and AI countries alike. For an AI country short a month before its deadline,
`TE_TAX ai_obl_enacted` and the institution at the promised level on the next 1st (if
P16 shows the effect sets a target rather than a level, the promise still breaks: raise
`te_tax_ai_enact_lead_months`). Record how often the AI met a promise on its own, from
the met lines without an enactment before them. A bureaucracy or budget promise about
to break is renegotiated (`ai_renegotiated`), never broken by neglect.
Serves S6, S13. Result: ___

### PT-22 The native tax level and passage

Rule *on*. An AI country in deficit whose native AI raises its tax level mid-month.
Expect `ai_waiting reason=legitimacy_native_level` when the level's legitimacy penalty
is the only failing condition, then a pass attempt on the 2nd, after the 1st puts the
level back to Medium.
Serves S13. Result: ___

## Further checks

### PT-23 Payers and receipts per channel

Rule *off*, harness P01–P05: for wage, dividend, rural, head and consumption taxes,
the payer's deduction, the receipts and the eligible counts; a native level change; a
scripted and a native consumption add (P05, authority).
Expect payer deductions matching the rate, a level change not moving receipts, and the
authority cost of a scripted add recorded.
Serves S4. Result: ___

### PT-24 Relief

Rule *on*. Agricultural and regional relief; Choose States, Name, Drop; capture a named
state; `event te_tax_debug.8` (names the capital's state).
Expect only incorporated states listed and a fourth refused; Regional Tax Relief on the
named states from the 1st; a captured state loses it within a month (`relief_cleared`);
Cost to Members scaling with the population covered. Record whether agricultural relief
also reduces the rural assessment.
Serves S5. Result: ___

### PT-25 Goods catalog

Rule *on*. Tax, Exempt and Undo in the Goods Catalog; a staple offer.
Expect 39 rows with in-game names, the Taxed Goods count changing in the review, and
Trade Unions offering "Leave Grain untaxed" only when grain is their largest grievance.
Serves S4. Result: ___

### PT-26 Offers by stance and Force Through

Rule *on*. Offers from a Persuadable, an Opposed, a Red Line and a Marginal group; Force
Through.
Expect a Persuadable group to commit, an Opposed one only at 20 or more, a Red Line group
to offer only promises, a Marginal group's Accept grayed, Accept acting on the right
group, and Force Through listing its conditions and costing 5 legitimacy, 3 opposition
approval and 2 override capacity.
Serves S1, S6. Result: ___

### PT-27 Interest group views of the code

Rule *on*. A group's approval breakdown after migration, and after a bill that makes the
code count as another taxation law.
Expect "Endorses" or "Opposes the Tax Code" at the old law's ±1 or ±2, at most one such
line per group, and the new law's view from the next 1st.
Serves S11. Result: ___

### PT-28 Promises end to end

Rule *on*. An education promise through delivery and maintenance; a bureaucracy
promise failing; an institution promise through a bureaucracy deficit; Renegotiate; trust
recovery over 24 months.
Expect the deadline moving a month per deficit month (`obl_paused`), each outcome once,
"Failing n of 3", Renegotiate only once in force, and trust stepping back to neutral.
Serves S6. Result: ___

### PT-29 Save and load at each stage

Rule *on*. Save and reload with a draft open, a bill in debate, a passed bill waiting,
the month before its commencement, after it, the month before an expiry, and with a
promise in maintenance. Diff each pair with the save report.
Expect dates, revisions, commitments, promises and future changes preserved and no clock
restarted (the diff reports "same" for every group).
Serves S7. Result: ___

### PT-30 Moved capital and formations

Rule *on*. Move the capital of a country with regional relief; form Germany or Italy.
Expect the relief to stay on the states named (it follows states, not the capital); the
formed country to migrate from its taxation law with no `migration_discrepancy`.
Serves S9. Result: ___

### PT-31 Scheduler retest

Rule *on*. `event te_tax_debug.5` in January; then the same after `event
te_tax_debug.6`; `event te_tax.1` twice in one month; an extension and a permanent bill
before an existing expiry.
Expect `TE_TAX commenced` on Feb 1 and `TE_TAX sunset` on Mar 1; `skip already
processed`; a late package `held_missed`, never commenced late; the watchdog never
followed by `commenced` without `process`; December and January dates printed right.
Serves S2, S3. Result: ___

### PT-32 Base-game journal entries and Traditionalism

Rule *on*. Russia's Great Reforms, Portugal's Our Fortunate Regeneration and
Imperialism of Promise with a qualifying code; a draft levying wage tax under
Traditionalism.
Expect the entries to complete with the counts-as line in their tooltips (rule *off*: the
vanilla tooltip), and Introduce refused under Traditionalism with its tooltip line.
Serves S1, S11. Result: ___

### PT-33 Open both hosts in every state

Rule *on*. Open the journal entry and the Budget tab with no draft, a draft, a bill and
waiting packages.
Expect no "Failed to fetch variable", data-context, "Unknown" or "failed reading
property" lines in `debug.log` or `error.log`.
Serves S12. Result: ___

### PT-34 Amendments on the carrier

Rule *on*. A code with all five taxes; change the wage tax from 4 to 6 by bill; check the
sponsor group.
Expect all five collecting together, the old amendment removed and the new one added in
one sync despite `can_repeal = { always = no }`, no approval or notification on the
sponsor, and no amendment cap reached.
Serves S4. Result: ___

### PT-35 Old saves and the probe harness

Load a save made before this release with the rule *off*.
Expect no error from the probe harness's carrier law records, and the game unchanged.
Serves S11. Result: ___

### PT-36 The carrier law is put back

Rule *on*. `event te_tax_debug.1` (activates Per-Capita Taxation over the carrier); also
on the rebels after an outbreak.
Expect `TE_TAX reasserted` the same day and the Legislated Tax Code back in the law
panel; the next day a sync and `TE_TAX drift … amend=N`; collections unchanged; no
`reasserted` loop.
Serves S5. Result: ___

### PT-37 Failed passage changes nothing

Rule *on*. Discard a draft; withdraw a bill; try to pass an empty bill, one with
legitimacy below 25, and one past its month; save and reload after the discard.
Expect no change to collections, approval or trust; the Pass tooltip listing each
failing condition once; a closed bill showing only that a bill is under debate.
Serves S1. Result: ___

### PT-38 Overlapping bills and a changed baseline

Rule *on*. Pass bill A on the wage tax, then bill B on the same tax with an earlier
month; open a draft that changed the wage tax before B passed.
Expect history "Part of a bill passed earlier was replaced by a new one", A's slot freed
if nothing is left in it, and the draft's row marked Changed Since Drafted until Accept.
Serves S3. Result: ___

### PT-39 Mod and base-game content under the rule

Rule *on*. Spectrum Crunch's option A; Cultural Hegemony's law pressure; the base game's
tax negotiation option.
Expect the spectrum option to add its two modifiers and change no dividend tax (rule
*off*: the original effect); Cultural Hegemony never to pick a taxation law; the
negotiation's tax level pinned back to Medium on the 1st (a known limitation).
Serves S11. Result: ___

### PT-40 Overview, enacted code and history

Rule *on*. Read the overview, Enacted Code and History after the game starts, after a
commencement and after an expiry; collapse and reopen each section.
Expect "Tax Code, Version N", a history row for the migration, expiry cells like
"→ 0.43 from 1842.12" without elision, and collapsed sections staying collapsed.
Serves S12. Result: ___

### PT-41 Workbench controls and the locked tab

Rule *on*. Click, shift-click and right-click the − and + of each tax; move Takes Effect
and an expiry; hover the Tax Code tab of a country without a code (a decentralized
one, through the console's tag switch).
Expect right-click to take a tax out of the draft without triggering the shift-click,
Takes Effect bounded to next month through 60 months, the footer only on the tab with a
draft open, and the locked tab's tooltip list rendering under "Not open yet".
Serves S1, S12. Result: ___

### PT-42 Script forms never used before in the mod

Rule *on* (*customs* for the two customs items). A watchdog sync after an expiry (a
local variable on a comparison's right side); a customs-only bill when its market is lost;
an adoption count in the history; a regional estimate (`multiply = owner.<value>`). The AI
layer's forms: `modulo = te_tax_ai_cadence_months` (a named value as the operand: if no AI
country ever introduces a bill outside an emergency, try a literal 3), the stored
`random_list` phase draw (AI countries' `te_tax.8` lines should spread over days 5, 12, 19
and 26), a local variable read inside a scripted trigger in the same execution (the
initiative's raise pick, `te_tax_pick`), the same local variable passed through a
parameter into a `limit` (`$INST$`, the picked instrument's step), the inline
`ig:<group>.ig_clout` multiply in each pre-score `te_tax_ai_cost_<key>`, and the
128-branch offer-acceptance chain's cost. Observables for the pre-score: `event
te_tax_debug.3` prints five pre-scores that are nonzero and differ by tax, and a T1 bill
then raises the taxes it ranks cheapest.
Expect each to load without a `debug.log` error and to print or do the right thing.
Serves S3, S5. Result: ___

## Script profiler

In the console, `Script.Profiling.Gui` opens the profiler; `Script.Profiling.Start`,
`Stop` and `Restart` control capture. The binary also carries `ScriptProfiling.Enable`
and `ScriptProfiling.Dump`, which write `logs/script_profiling.txt` with call counts
(verified 2026-10-03; the dump records triggers, script values and some effects, not events or on_actions, so read `te_tax.8` from the GUI). The profiler names files by basename only, and a
journal entry's monthly pulse appears as `event (immediate) @ <file>:<line>`. Scripted
GUI `is_shown` blocks and display values appear only while their panel is open, so note
which panels were open. (From the late-game performance work, commit 6815868c.)

## Retiring the probe harness

After the owner's probe pass, the harness is deleted in its own PR. Its files: the
`te_debug_tax*` script, GUI and loc files (`common/amendments/`, `common/laws/zz_te_debug_tax_carrier.txt`,
`common/on_actions/`, `common/script_values/`, `common/scripted_effects/`, `common/scripted_guis/`,
`common/scripted_triggers/`, `common/static_modifiers/`, `events/te_debug_tax_events.txt`,
`gui/te_debug_tax_widgets.gui`, `localization/english/te_debug_tax_l_english.yml`), and, unless
P09b or P09c passed and a customs follow-up kept them, the customs probe's registrations
(`common/modifier_type_definitions/te_tax_probe_modifier_types.txt` and its 24 loc keys in
`localization/english/te_modifiers_l_english.yml`). The tax code's own console
(`events/te_tax_debug_events.txt`, `te_tax_debug.*`) is not harness and stays.

Its hooks in production files must change with it: the Tax Probes tab in
`gui/te_systems_window.gui` and `te_window_launcher_sgui` (`te_system_tab_sguis.txt`); the
`te_tp_observe_controls` calls in `banking_policy_effects.txt` and
`te_monetary_arrangement_effects.txt`; the `te_tp_lock` test in both gates of
`common/scripted_guis/te_tax_native_sguis.txt`; `organize_loc.py`'s `DEBUG_TAX` category and its
tests; `scripts/i18n/translate_loc.py`'s `DEV_ONLY_FILES`; and the harness exemptions in
`test_tax_code_bypass.py`, `test_tax_code_customs.py` and `test_tax_code_state.py`.
`gui/budget_panel.gui` holds no harness mark any more, whatever
`docs/testing/tax-code-probes-extended.md`'s older list says. `te_tp_` is not unique to the
harness: the trade-partner chart's `te_tp_import_markets` and kin stay.

Saves made since #585 hold the probe carrier's law records, so PT-35 runs before and after the
deletion.
