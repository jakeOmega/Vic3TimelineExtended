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
