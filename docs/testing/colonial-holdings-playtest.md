# Colonial Holdings play-test checklist

What the next play-test should look at in the Colonial Empire panel's Colonial Holdings section (2026-10-24): the
territory and colonial-subject lists, their per-row buttons and the three confirmation popups they open
(`decolonization_events.402`-`.404`). In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and
the play-test list"): the section landed on the offline gate, and this list holds what only the game can show. Add new
sections newest last, and strike through a fixed item with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The Colonial Empire journal entry, or the Colonial Empire tab of the Timeline Extended window:
  the overview's "Colonies · Colonial subjects" line, then Colonial Holdings, the first section under it.
- **Quick setup.** A 1950s save of an empire with overseas colonies and at least one Colony subject and one
  Protectorate (Britain, France or Portugal after researching Decolonization). `event te_debug_colonial_empire.2`
  opens each popup for the largest target through the rows' own effects (options h, i, j), if a row's button will not.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `colonial_empire_release_state_sgui`,
  `colonial_empire_free_subject_sgui`, `colonial_empire_dominion_subject_sgui`, `Failed to fetch`, `je_colonial_empire_subject`
  and `decolonization_events.40`.

## The lists (2026-10-24)

| Check | Expect | If it fails |
|---|---|---|
| **The overview line.** Hover "Colonies: N · Colonial subjects: N" under Next band. | The two counts match the lit colony icons in Territories (all of them, beyond the eight rows too) and the subject rows; the hover gives both tests with their thresholds. | Zeros on a running entry: the snapshot did not run (`colonial_empire_refresh_display`), or the line reads `colonial_empire_disp_colonies` / `_subjects` before the first pulse of an upgraded save, which shows the pending line instead. |
| **Territory rows.** Open Colonial Holdings. | Up to eight rows, the name's hover giving the population, Primary, SoL and GDP in their columns, and a Release button at the end of each row, inside the panel's width. | A clipped button: narrow the name cell (`te_ce_territory_row`, 210) and the head's to match. |
| **Subject rows.** With a Colony and a Protectorate subject. | Each row shows the flag (click opens the country), the name, vanilla's subject-type icon (its type name and why it counts on hover), liberty desire (its level and weekly change on hover), GDP, then Release and Dominion. | A blank flag, icon or figure means a vanilla getter does not work on `Var('colonial_empire_subject_N').GetState.GetCountry`: show the subject through a scripted GUI's `ExecuteTooltip` instead (gui_modding_guide gotcha #11, way (b)), and move liberty desire to a script value. |
| **The liberty-desire head.** Look at the subject list's column heads. | Vanilla's liberty-desire concept icon over the figures, with its hover. | A missing texture: replace the icon with the word "LD" in the small font. |
| **"+N more".** With nine or more of either. | The territories' hover names the rest by GDP; the subjects' lists every colonial subject with why it counts. | A raw key in the subjects' hover: `je_colonial_empire_subject_more_line`'s `GetCustom` on `THIS.GetCountry`. |

## The buttons and their popups (2026-10-24)

Each button passes its row's state to a scripted GUI as a saved scope (`AddScope( 'ce_state' | 'ce_capital',
State.MakeScope )`), the shape the Grand Monument rows ship, and the effect saves the target for the popup.

| Check | Expect | If it fails |
|---|---|---|
| **Release a territory.** Press Release on an eligible territory. | A popup at the territory: "The Future of X", naming the people who would form the new country and how many states would go. Grant it independence and Reconsider are offered; the Round Table is enabled or greyed with "This option is unavailable because:" and its reasons. | Every button greyed with no reason: the saved scope did not arrive (`exists = scope:ce_state` failed). Pass the slot number as an op code instead and read `var:colonial_empire_territory_<N>` in script. A blank culture or state count: the saved scopes of the effect did not reach the event; store them as variables on the empire. |
| **The Round Table hover.** Hover Release on a territory with a severely unaccepted population, then on one without, with authority above and below 200. | The hover's last line says whether a Round Table is open, and why not. | No line: the effect's `if` branches do not render in `ExecuteTooltip`; say it in the popup only. |
| **Grant it independence.** Choose it. | The territory and its homeland region become a new country; the list loses it at once; +1 stability a month for 8 months; Peaceful Decolonization only if we did not hold it. | The list keeps the territory until next month: the option's refresh did not run (`has_journal_entry` guard). |
| **One at a time.** Press Release on one row, then on another, before answering. | The second is greyed: "No other decolonization decision is waiting for our answer". After Reconsider, both work again. | Not greyed: `decol_offer_pending` was not set before the second click was evaluated. |
| **Left unanswered.** Open a popup and let the days run past its duration. | Reconsider is taken: nothing released, the lock cleared. | A release: an option other than Reconsider was taken by default. |
| **Release a subject.** Press Release on a Colony subject. | "Independence for X": the subject becomes independent, receives "Independence Granted" naming us, and is a former colony (the post-independence events can reach it). Under Neocolonialism a second option frees it on terms. | The popup names no subject: the capital's owner was not saved; pass the subject through a variable. |
| **Dominion.** Press Dominion on a Colony subject. | "Dominion Status for X": it becomes a Dominion, liberty desire falls by 30, vanilla's Increase Autonomy is on cooldown for it, and it leaves the list (no longer colonial). | Still a Colony: `increase_autonomy` did nothing; use `change_subject_type = subject_type_dominion` behind `is_country_type = colonial`. |
| **Dominion greyed.** Hover Dominion on a Protectorate, a Chartered Company and a subject's own subject. | Greyed: a protectorate or chartered company has no looser kind; a subject's subject is not ours. | |
| **The last holding.** Free or raise the last colony and subject. | The entry ends voluntarily: The Last Flag Lowered after a release you chose, The Colonial Chapter Closes after a dominion alone. | |
| **The Timeline Extended tab.** Repeat one button from the window's Colonial Empire tab. | The same rows and buttons, acting the same. | |

## Settled land and the people a release forms (2026-10-24)

The owner's report: British Guatemala, 75% English, was listed and released as its 7.7% Irish. Settled land (more
than `colonial_settler_majority_share` of the people of our primary cultures) is now no colony and no territory, and
every release forms with `decol_choose_release_culture` (the largest homeland culture present, else the largest
culture that is not ours, each culture counted whole). The pick sums pops into local variables
(`decol_release_culture_weigh`), a form the demographics probe proved; the threshold reads
`colonial_territory_primary_share_value`, the share the Primary column already showed.

| Check | Expect | If it fails |
|---|---|---|
| **Settled land leaves the list.** As Britain, a state like British Guatemala (more than half English) after the monthly refresh. | Not in Territories and not counted in the overview's Colonies; still a colony if it was not settled land. | Every territory gone, or none: `colonial_state_settler_majority` misreads the share; check a row's Primary figure against the population tab. |
| **The release names the right people.** Release a territory whose homeland people are absent (several minorities, none at home). | The popup names its most numerous culture that is not ours, counted over all its pops; Grant it independence forms the country with that culture. | The popup and the new country disagree: the preview and `form_decolonized_country` read different pops (a month between them) or the local variables did not carry across the state-to-pop scope change; log `decol_release_culture_best`. |
| **"Goes alone."** Release a territory with no neighbouring homeland state of ours. | "If it goes, it goes alone, as a nation of its X people." With a region: "...it takes with it ... N states in all." | "1 states in all": `decolonization_region_1_count` was unset when `.402`'s desc was evaluated. |
| **A collapse spares settled land.** `event te_debug_colonial_empire.1`, Collapsing (10), then let the bar drain to 0. | Up to three successor countries, none from a state that is more than half our people. | |

## Release blocs: one row for the states one release takes (2026-10-24)

The owner's request: Henan and Southern Anhui, neighbours and both homelands of the Han alone, were two rows though
releasing either takes the other. Each row is now a bloc (`colonial_empire_mark_release_blocs`, monthly, players
only): a territory and the states its release would take, shown at its largest state with "+N". Forms new to this
panel, none read in game yet: a culture held in a state variable (`colonial_bloc_culture`) and read in a tooltip
through `var:x = { save_temporary_scope_as }`, and `ordered_in_list` over a variable list held on a state.

| Check | Expect | If it fails |
|---|---|---|
| **One row per bloc.** As a European power holding Henan and Southern Anhui (or any two neighbouring territories sharing their only homeland culture). | One row, "Henan +1" (the larger state first); the GDP is both states', and Release on it opens `.402` naming 2 states. | Two rows: a member was not covered, the culture comparison failed (`scope:colonial_bloc_member_culture = { this = scope:colonial_bloc_culture_pick }`); compare `decol_release_culture_best` for each. |
| **The name's hover.** Hover a bloc's name. | The people it would form ("Released, it forms a nation of its Han people."), "one release takes all 2 of these", each state with its people, then the weight on stability. | No people line: the culture variable did not hold a culture scope; store the culture's key as a flag instead. No state lines: `ordered_in_list` on a state's list failed; walk `every_scope_state` with a `colonial_bloc_of` variable instead. |
| **A different release keeps its row.** A territory whose largest homeland people differ from its neighbour's (a Hui-majority state beside Han ones). | Its own row, and it also appears in the Han bloc's hover, since the Han release would take it. | |
| **"+N more".** With more than eight blocs. | The rest by the bloc's GDP, a bloc as "X +N: £GDP". | |
| **The monthly cost.** A large empire (China, Britain) on the monthly pulse. | No visible stutter at the month's turn. | Limit the pass to the eight largest seeds plus a count, or move it to the panel's open. |

## The panel after the GUI audit (2026-10-27, issue #1210)

The audit's Colonial Empire findings (CE-1 to CE-11, `docs/audits/gui_audit/monuments_colonial.md`) reworked the
panel offline. The territory and subject lists are datamodels over every bloc and every subject
(`colonial_empire_blocs`, `colonial_empire_subject_capitals`), so the "+N more" checks above no longer apply: every
row has its own figures and buttons. International Pressure is a table of great powers, one script container a row
(`colonial_empire_gp_rows`). The overview is four of Banking's cells. Every text is at the house sizes, 17 for rows,
20 for subheadings and 16 for the overview.

### Self-checks

| Name | What it checks | Where | If BROKEN |
|---|---|---|---|
| `ce_subject_row` | A subject row of the datamodel reads its country through `State.GetCountry` (proven before only from a stored variable, gui_modding_guide gotcha #15). The first row drawn in a game reports once: OK when the row read the subject's name, BROKEN when it read none though the capital has an owner. | `te_ce_subject_row`'s two 1x1 widgets, `colonial_empire_selfcheck_subject_sgui` | Store each subject's capital on a script container (`colonial_empire_gp_row`'s shape) and read `ScriptContainer.MakeScope.Var('x').GetState.GetCountry`, the covert rows' proven chain, or show the subject through a scripted GUI's `ExecuteTooltip` (gotcha #11, way (b)). No line at all after a subject row has shown means the `_show` state did not fire: check the row is drawn, then the Grand Monuments naming line's precedent. |

### Checks

| Check | Expect | If it fails |
|---|---|---|
| **Every row.** As an empire with more than eight territories or subjects (Britain, France). | Every bloc and every subject has a row with its figures and buttons, largest GDP first; the hovers of the colony icon, the figures, the name and the buttons all show (they read `GetPlayer`, not `JournalEntry`). | An empty list on a running entry: `GetList` over the stored list is not drawn; check `colonial_empire_blocs` on the country in the save. An empty hover in a row: a key in it still reads `JournalEntry` (gotcha #24). |
| **The great powers' table.** With a condemner and a supporter (`event te_debug_colonial_empire.2`). | A row each, condemners first: flag, name, "Condemning"/"Supporting", prestige and the stability a month ("-0.84/mo"); the row's hover gives the factor against our prestige. The rows' figures add up, with any escalation line, to the "Great Power pressure" row of Why Stability Is Moving. | A blank flag or name: `ScriptContainer.MakeScope.Var('ce_gp_capital')` did not reach the country. Rows from last month left over: `colonial_empire_clear_gp_rows` did not destroy them. |
| **The escalation lines.** Push the condemners past a third of great-power prestige: `event te_debug_colonial_empire.2` sets condemners. | "Diplomatic isolation -1.00/mo" under the table, and at two thirds "International consensus -2.00/mo" as well; the overview's Great Powers cell reads "Isolated" (orange) or "Consensus" (red). | |
| **The overview's cells.** Look at the four cells in each band. | Band: the band's icon and name, and "Stable at 65" under it below the top band (its hover the next band's line). Great Powers: the escalation word and the net a month. Holdings: colonies and subjects. Programmes: three small programme icons, lit while each runs, "N of 3 running" and their stability a month. Nothing elided. | A word elided at 16: shorten it in `te_journal_entries_l_english.yml`; the test budgets 8.6 units a character. |
| **The type sizes.** Read the lists, the programme rows and the overview at 1080p. | Rows and buttons at 17, subheadings at 20, the overview at 16; no column head or button label cut short ("Accords Signed", "Dominion", "Ours"). | Widen the cell and narrow the name column, or shorten the label; `WidthBudgetTest` holds each to the estimate. |
| **The programme rows.** Open Colonial Programmes. | Each row: the short name, "1 / 3", its stability a month in colour, then minus and plus. The hover gives Upkeep and One-off lines, what a level adds, and the full program's modifiers. | |
| **The concepts.** Hover "colonial territory", "overseas colony" and "colonial subject" in the Holdings hovers. | Each concept's definition with its thresholds from script (population, shares, acceptance, standard of living). | Blank thresholds: `GetPlayer.MakeScope.ScriptValue` does not render in a concept's description; type the values from `colonial_empire_values.txt` instead. |
