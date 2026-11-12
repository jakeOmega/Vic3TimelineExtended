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

## Our Stance on Colonialism and The Colonial Powers (2026-11-03)

The two sections that outlive the entry, and the tab that opens with Decolonization alone
(`te_ce_sec_stance`, `te_ce_sec_powers`, `te_ce_readout`; script in
`common/scripted_effects/decolonization_stance_effects.txt`). Quick setup: a 1950s great power with no colonies (the USA)
for the readout, and Britain or France for the entry's view. Search `debug.log` for `colonial_empire_stance_sgui`,
`decol_world`, `ce_pw_` and `Failed to fetch`.

| Check | Expect | If it fails |
|---|---|---|
| **The tab without the entry.** As the USA after researching Decolonization, open the Colonial Empire tab. | The tab is enabled; its hover is the readout line. Under the header: "The rest of this tab comes with…" (its hover the entry's checklist), then Our Stance on Colonialism and The Colonial Powers. No overview, no Open Journal Entry button. | A blank tab: the readout's gate (`te_window_colonial_empire_readout_sgui`) or `tab_before_gate` did not draw; the generated strip's `enabled` is `Or(…)` of the two gates. |
| **The tab after the entry ends.** Complete or fail the entry (`event te_debug_colonial_empire.1`, or give away the last colony). | The tab stays open on the readout, its line saying secured, collapsed or no colonies. | The tab greys: the research test (`ce_tab_unlocked`) does not hold. |
| **The stance lines.** Read Stance, In force and Next change; hover each. | "Neutral / No stance held / Now" at first. After Condemn: "Condemns colonialism / Yes, for 150 influence / In 24 months"; the stance's hover lists Anti-Colonial Policy's effects (`GetStaticModifier(...).GetName` and `.GetDesc`). | A raw `GetName` on the hover: drop the name and keep `GetDesc`. Months that do not count down: `decol_stance_monthly` did not run from `decolonization_events_on_action`. |
| **The buttons.** Hover each of Condemn, Stay Neutral and Support, then press Condemn. | The current stance's button is greyed "It is not our stance already"; during the 24 months every button is greyed with the cooldown line; a non-great power's Condemn and Support are greyed with the great-power line. The hover's second half shows the stance's line, Anti-Colonial Policy and the four interest groups' reactions. The influence breakdown gains a 150 cost. | No modifier line on the hover: the core's `if` limits are read before the effect, as expected, but the rank test failed; check the country is a great power. |
| **The Colonial Question.** As a great power that has not seen it, research Decolonization with a colonial empire in the world. | It fires once, its description pointing to the tab; Condemn and Support greyed without 150 influence; Neutral the default. It does not fire again for the player. | It repeats: `decol_stance_asked` was not set in `immediate`. |
| **The Colonial Powers.** Open the section; wait a month. | Up to eight rows, largest first: flag (click opens the country), name, People, Status (Not begun, a band, Secured or Collapsed, each with its hover), Stability as "55%" or "—". The row's hover gives what our stance does to it a month; after pressing Condemn it changes at once. | Blank names or flags: the container's `Var('ce_pw_capital').GetState.GetCountry` chain (International Pressure's rows use the same). Every Stability "—": `colonial_je_total_months` or `colonial_empire_bar_bucket` missing on running empires. No rows at all: `ordered_country` found no colonial power; check `ce_power_colonial_population` (`scope:x.value` read in `decol_world_power_row`). |
| **A great power that falls in rank.** Use the console to lower a great power holding a stance below the rank, then wait a month. | In force reads "Dormant: not a great power"; the influence cost and the policy modifier are gone; Stay Neutral is still enabled. | The modifier stays: `decol_stance_refresh` did not run. |

## Pressure, the cap and who backs the colonial powers (2026-11-03, second pass)

The owner's four asks: the AI backs colonialism more often with Colonial Resettlement or Exploitation, colonies of its own or a partner's, or an illiberal government (`decol_ai_colonial_laws`, `decol_ai_illiberal`, Support's adds in `decolonization_events.14`); each country's tab gives its share of great-power prestige (Our Stance's Prestige share line) and International Pressure lists each power, with its share, on any country's panel; condemnation a quarter weaker (−0.45 a power, −0.75 and −1.5 for the escalations); the monthly cap 1.5. None of it seen in game yet.

### Checks

| Check | Expect | If it fails |
|---|---|---|
| **Another country's pressure.** National Info → an AI empire's Colonial Empire tab (Britain or France while its entry runs), the month after loading. | International Pressure lists its condemning and supporting great powers with flag, name, stance, share and monthly effect, as your own tab does; no "own panel" note. The row hover speaks of "the empire"; the "none" line reads "the country" when nobody presses it. The overview's Great Powers hover counts them. | Empty for every AI: `colonial_empire_refresh_gp_rows` still gated (it is called from `colonial_empire_refresh_display`, monthly). In the first month after loading an older save the section shows "The figures appear after the next monthly assessment" (`colonial_empire_disp_gp_rows_built`), and the Great Powers hover counts 0: expected until the empire's next pulse. |
| **The shares add up.** On any empire's tab, add the Share column's condemners. | They sum to the overview pie's Condemning figure, and the supporters to Supporting, within rounding. | Off: `ce_gp_share` divides by another pool than `colonial_gp_prestige_pool` (`colonial_empire_gp_pool`, set before the rows). |
| **Prestige share line.** Our Stance on Colonialism on your own tab, then National Info → another great power's and a lesser country's. | A great power shows "N% of the great powers'"; the great powers' figures add up to about 100%; a lesser country shows "None: not a great power". | Every great power "None" or 0%: the global total is missing (`decol_gp_prestige_on_action` on `on_monthly_pulse`) and the fallback walk failed. Figures summing well over 100%: the total is stale or counts too few powers. |
| **The cap.** Why Stability Is Moving under heavy pressure, and the Help page's stability topic. | Monthly limit holds the change at −1.50; the Help page says ±1.50. | Still ±1.67: an old `colonial_stability_drift_cap`. |
| **Who supports.** An observer run into the 1950s; read International Pressure on the colonial great powers every few years. | More supporters than before the pass: illiberal great powers (autocracies, oligarchies, single-party states), those under Colonial Resettlement or Exploitation and allies of an empire back the empires a fair share of the time; elected powers without colonies still mostly condemn. | Nobody supports: check `decol_stance_ai_can_hold` (influence) first, then the weights. Everyone supports: lower the +8s. A Council Republic backing empires more than a typical power: `decol_ai_illiberal`'s Council Republic exclusion did not hold (it should read like a typical power, Condemn 87-98%). |

## Starting again after it ends (2026-11-03)

The owner's report: failing the entry did not let it come back, in a 1910 save. The engine deletes a finished
`je_colonial_empire` record, failed or completed, and never activates the type again: that save holds no record of it,
active or inactive, for Britain, France, Spain, the Netherlands or the USA, against an inactive one on 211 other
countries. A monthly pass now adds the entry back (`ce_reentry_monthly`, `common/scripted_effects/decolonization.txt`,
run from `colonial_geography_on_action` straight after the separation cache's step) once a country has been due it for a
whole month (`ce_reentry_due`, `colonial_empire_triggers.txt`: the entry's research and `possible`, not decentralized,
not a revolution's rebels, no record of the entry, active or inactive, and a year since a voluntary end; over an
inactive record the add is refused, #1416). So a collapse waits ten years and a
secured empire never returns, as the rules always said. A voluntary end sets no cooldown, but the pass waits a year after
one (`ce_reentry_voluntary_hold`), a guard against a colony test that flickers. Every modifier an ending adds is now
refreshed, not stacked, since a second ending is reachable. Search `debug.log` for `TE_CE_REENTRY` (one line per add)
and `ce_reentry`.

What the save shows (its history charts, read with `scripts/analysis/save_country_probe.py`): Britain's entry started
about 1897.10 at 50, fell at the monthly cap of 1.67 to 0 by 1900.04 and collapsed, so its ten-year cooldown ran out a
few weeks before the save. France (1898) and Spain (1898) collapsed the same way, and had been free of the cooldown for
about two years without the entry. The USA's ended at 30 in 1897, a voluntary end, and it holds no separated state now,
so it does not return. Britain holds 18 states the cache marks separated from London (Kenya, Tanganyika, Lindi, Rift
Valley, Amhara, Ceylon, Fiji, the Solomon Islands and others), so it is very likely due the entry again; whether each
state passes the rest of the colony test needs its pops, which the probe does not read.

### Self-checks

| Name | What it checks | Where | If BROKEN |
|---|---|---|---|
| `ce_reentry` | `add_journal_entry` brings back an entry type the country has finished (no vanilla precedent re-adds a finished type of its own). The pass marks each country it adds the entry to, naming the country, and notes whether its entry had run and ended (`colonial_empire_has_ended`, set at every ending since this change). The next monthly pass reads the mark before it can add again. One line per add: OK when the entry is running, BROKEN when it is not though the country is still due it, each with `ended_before=yes` or `ended_before=unknown`. Only `yes` answers the question: `unknown` is a country that may never have held a record (the engine leaves some out), or one whose entry ended before the variable existed (Britain in the 1910 save). A country no longer due it gives no verdict, nor does a revolution's winner holding the loser's mark. | `ce_reentry_monthly`, step 1 | BROKEN with `ended_before=yes`: the entry stays active through a failure, as a dormant phase in place of `fail`. A collapse or the last colony's loss runs its outcome and sets its cooldown as now, then leaves the entry dormant until the country is due it again. Until then every add is wasted: one `TE_CE_REENTRY` line per due country every two months. BROKEN with `ended_before=unknown` only: `add_journal_entry` gave a country no entry at all; read the `debug.log` lines around it. |

### Checks

| Check | Expect | If it fails |
|---|---|---|
| **The owner's 1910 save.** Load `new york_1910_05_13.v3` (the owner's save folder) and run two months. | At the second monthly pulse after loading (by mid-July 1910) `debug.log` has `TE_CE_REENTRY: added je_colonial_empire to United Kingdom`, and the same for France and Spain if they still hold a colony. National Info, United Kingdom, Colonial Empire shows the entry's panels at stability 50, and The Colonial Powers' row for Britain reads a band, not Not begun. | No line for Britain: it is not due. Run `event te_debug_colonial_empire.4` as Britain (the colony test's census, `TE_CE_CENSUS`) to see whether any state passes. A line but no panels: see the self-check. |
| **The self-check line.** Run a third month. | One `TE_SELF_CHECK OK ce_reentry country=GBR name=United Kingdom ended_before=unknown …` per add (Britain's entry ended before `colonial_empire_has_ended` existed). The `ended_before=yes` line that settles the question comes from an entry that ends after this change and returns: the voluntary end below. | BROKEN: take the fallback above. No verdict at all after an add line: the country stopped being due within the month (its colony test moved); wait for the next add. |
| **One entry, not two.** As a country that has never run the entry, take its first colony after researching Decolonization. | The engine starts the entry within two weeks, as before; no `TE_CE_REENTRY` line for that country, and one Colonial Empire entry in the journal. | Two entries: the pass raced the engine's activation of the country's inactive record; wait two months instead of one (a second mark). An add line with one entry is not a race: the country held no record (the engine leaves some out, as Banking's self-check found), and the pass gave it the entry. |
| **A voluntary end, then a colony again.** Release the last colony and colonial subject (the entry ends with The Last Flag Lowered), then take a colony back (a war, or the console). | The tab's readout says the entry starts again within two months of holding one, and no sooner than a year after it ended; its checklist shows the year's line unmet. A year after the end, within two months, it runs again: stability at 50, every program at level 0, Months Held at 0. The next pass logs `TE_SELF_CHECK OK ce_reentry … ended_before=yes`. A second voluntary end refreshes Post-Imperial Standing (or Negotiated Withdrawal) rather than adding a second copy. | It never returns: check `debug.log` for the add line and the self-check. Programs left running: `colonial_empire_je_cleanup_effect` did not clear the levels. Two copies of the modifier in the country's modifier list: the removal before the add did not run. |
| **A collapse waits ten years.** After a collapse (`event te_debug_colonial_empire.1`, Collapsing, then let the bar reach 0), keep a colony. | No add line while the readout says the system collapsed; within two months of the cooldown's end, the entry runs again. | An add during the ten years: `ce_reentry_due` misses `colonial_empire_collapsed_recently`. |
| **A second collapse.** Let the returned entry collapse too (`event te_debug_colonial_empire.1`, Collapsing). | A colonial subject that went through both collapses holds one Imperial Collapse Aftershock (`country_liberty_desire_add` +0.50, not +1.00), and the country one Colonial Empire Collapsed or Negotiated Withdrawal. | Two copies: `remove_modifier_if_exists_effect` did not run before the add in `on_fail`, `.201` or `.204`. |

## The AI's stance on colonialism (2026-11-03, issue #1370)

The AI no longer condemns the colonialism it practices: The Colonial Question (`decolonization_events.14`) never gives
an empire Condemn, halves Condemn's weight for a regressive power (again for a slaveholding one) and for a partner of an
empire, and the monthly pass (`decol_stance_monthly`) drops Condemn from an AI empire once its 24-month cooldown is
over. Design:
`docs/systems/mod_systems/decolonization.md` § The AI's Stance on Colonialism. **What right looks like** is the
system's design target (that doc's Overview): "most colonial powers except the top 2-3 GPs will lose most of their
colonies". Quick setup: the owner's 1910 save (`new york_1910_05_13.v3`, where twelve great powers condemned and none
supported), or an observer game from 1836 to the 1950s. Read stances in the save (`gp_anti_colonial_stance`,
`gp_pro_colonial_stance`) or on each power's Colonial Empire tab through National Info, and the bars on the Colonial
Powers list. Search `debug.log` for `ai_condemn_factor_order`.

**Who condemns less.** Racialized Citizenship and the slavery laws count as regressive, and they are common starts:
vanilla starts the USA, Brazil and Belgium on Racialized Citizenship and Brazil and the Ottoman Empire (TUR) on the
Slave Trade. In the 1910 save the regressive condemners without an empire are the USA and Brazil (Racialized
Citizenship), TUR (Slave Trade) and India (BHA, Debt Slavery). A regressive power condemns at 62-80% instead of 87-98%
(Condemn 13-19.5 : Neutral 5 : Support 0-3, against 26-39 : 1 : 0-3), and at 33-49% when it is also allied with an
empire; slavery halves Condemn again (owner, 2026-11-03), so TUR and India condemn at 45-66%, or 20-33% beside an
empire. This is intended: a segregated or slaveholding power is a less convincing anti-colonial champion until it
reforms.

### Self-checks

| Name | What it checks | Where | If BROKEN |
|---|---|---|---|
| `ai_condemn_factor_order` | `ai_chance` applies its modifiers in order, so the `factor = 0` placed after Condemn's adds holds an empire's weight at 0 (at least 11 before it). No vanilla script shows that order matters. Once a game each: BROKEN when an AI that holds a colony, a colonial subject or the entry takes Condemn in `.14`; OK when such an AI takes Neutral or Support while it had the influence for Condemn. One OK is weak evidence, because a wrong order still leaves Support a share; read the verdict as no BROKEN line over a full observer run. Lines carry `country=` and `date=`. | `decol_selfcheck_empire_condemned` / `_declined`, `decolonization_stance_effects.txt`, called first in each of `.14`'s options | Make Condemn's weight one script value that order can't change: `decol_ai_condemn_weight` in `decolonization_stance_values.txt`, a `value` with `if` blocks that adds the terms, multiplies by the two halves and sets 0 for an empire or without the influence; then `.14`'s option a reads `ai_chance = { base = 0 modifier = { add = decol_ai_condemn_weight } }`, or the engine's equivalent. |

### Checks

| Check | Expect | If it fails |
|---|---|---|
| **Old condemnations go.** Load the 1910 save and play a month. | Every AI that holds a colony or a colonial subject, or runs the entry (Britain, France and Spain, if their collapses left them colonies), drops Condemn at the first monthly pulse, or when its 24-month cooldown from its last change runs out. A power whose collapse left it no colonies keeps Condemn, by design (owner, 2026-09-26). The influence breakdown loses the 150 cost. | Still condemning after the cooldown: `decol_holds_colonial_empire` was false for it (check its Colonial Holdings counts), or `decol_stance_monthly` did not run. |
| **No empire takes Condemn again.** Play on to each empire's next Colonial Question (every three years for the AI). | It picks Support or Neutral, never Condemn; `TE_SELF_CHECK OK ai_condemn_factor_order` once. | A Condemn, with `TE_SELF_CHECK BROKEN ai_condemn_factor_order`: the factor 0 did not hold (take the self-check's fallback). A Condemn with no BROKEN line came from a UN Decolonization Resolution (issue #1373; it goes after 24 months). |
| **The bars leave the drift cap.** Watch the colonial great powers' stability through a few years (the Colonial Powers list, or the entry's history chart). | No longer at the cap (−1.5 a month since the second 2026-11-03 pass, −1.667 before) from the first month: the great-power pressure row is smaller and the bars fall more slowly, if at all. | Still at the cap: the condemners left are enough on their own; look at the International Pressure table for who condemns. |
| **The balance target.** An observer run into the 1950s-60s. | The top two or three colonial great powers keep most of their colonies; the smaller colonial powers lose most of theirs. Great powers without colonies, with an elected government and without a regressive or colonizing law (a reformed USA, a democratic France or Britain after their empires) still mostly condemn; the regressive ones (the USA and Brazil while on Racialized Citizenship; TUR and India, holding slaves, least of all), the illiberal ones (an autocratic Russia or China, a single-party state that is not a Council Republic) and allies of an empire more often stay neutral or support. | Every empire holds on: the empires now back one another and too few powers condemn. Lower Support's +10 for an empire or the +8s for a partner, a colonizing law and an illiberal government, or raise Condemn's factor for a regressive or slaveholding power or a partner (`decolonization_events.14`). Still collapsing within 34 months (30 at the old 1.667 cap): look for condemners that hold an empire (the review should have cleared them). |
| **The debug harness keeps its condemners.** `event te_debug_colonial_empire.2`, option a, then a month. | The International Pressure table keeps every condemner, the colonial great powers included: the harness sets the stance on every other great power, those already condemning too, and starts each one's 24-month cooldown. | A colonial great power's condemnation vanishes a month later: either the harness did not start its cooldown (`decol_stance_start_cooldown`; before this fix it skipped a power already condemning, such as Britain or Spain in the 1910 save, which the review then dropped), or the AI's influence went negative, a drop that ignores the cooldown (`decol_stance_monthly`'s first branch). Check the power's influence before blaming the review. |

## The nine endings and the two-pole bar (2026-11-12, #1432, #1434)

The entry's endings are nine outcomes, one each, so the journal panel lists them all with their conditions; the stability bar is a bar between two poles. `test_colonial_empire_outcomes.py` holds the triggers to the old dispatch offline. What only the game shows:

| Check | Expect | If it fails |
|---|---|---|
| **The panel lists nine endings.** Open a running entry's journal page. | The two federations, The Iron Fist Holds, The Commonwealth Path, Quiet Assimilation, The Empire Endures, The Last Flag Lowered, Negotiated Withdrawal and The Empire Crumbles, each named by its event's title (the headers splice `$decolonization_events.<n>.t$`), with plain-text conditions and the three programs' months as figures. At most one success and one failure ending shows its conditions met. | A raw `$decolonization_events…$` in a header: type the titles into the header keys. A condition printed as script: a test outside its `custom_tooltip`. |
| **A path ending fires its event.** `event te_debug_colonial_empire.1` to Solidified, run Garrison past 24 months and hold at 100 for 60 months (or the harness's shortcut). | The Iron Fist Holds concludes the entry, `.203` fires, and the concluded page shows "concluded with our colonies held by the garrisons". | Nothing concludes with the bar held: a trigger never passes; compare the counters in the tooltip with `colonial_*_months`. |
| **A collapse picks its ending.** Drain the bar to 0, once with Investment the longest program past 24 months and once with Garrison the longest. | Negotiated Withdrawal (`.204`) the first time, The Empire Crumbles (`.201`) the second; both set the ten-year cooldown and the subjects' aftershock. | |
| **The two-pole bar.** Look wherever the stock bar block draws `colonial_stability_bar` (the entry's page while it is not active, the concluded page if it shows bars). | Green fill over red, the sliding marker at the value, "Colonial Stability: collapse at 0" on the left and "integrated at 100" on the right. While the entry runs the overview's own five-layer row is unchanged. | A blank or magenta bar: a texture path is wrong; copy vanilla's `great_game_core_progress_bar` fields. |
