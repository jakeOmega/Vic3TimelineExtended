# In-game QA harness results: 2026-11-11, play-test rows on 1.15.1

The first play-test rows run through the harness (`python3 -m game_qa`, the `game-qa` skill) rather than by
hand. Each list's own row carries a one-line pointer here.

**Game:** Victoria 3 1.15.1. **Build:** `main` at `4d9b85393` (the 1.15.1 hotfix merge, #1594), deployed.
**Playset:** this mod only. **Save:** a fresh 1836 game made by the harness (`te_qa_fixture_81677a2162d5`).
**Launches:** three, with the owner's go-ahead for up to three; each restored the owner's files (`outcome:
restored`, nothing held).

| Session | Run folder (under the backup root) | What it was |
|---|---|---|
| 1 | `runs/20261111T181801Z/` | Country-select screen, 2 January 1836, time stopped. USA, then the Ottoman Empire |
| 2 | `runs/20261111T182536Z/` | Entered as the USA, 6 January to 6 April 1836 |
| 3 | `runs/20261111T183620Z/` | Entered; USA, Britain, France, 5 January to 17 February 1836: the cause of the Court Overhaul failure |
| Fixture | `snapshots/20261111T181530Z/run_logs/` | The unattended run that made the save, 1 to 4 January (pruned after five more snapshots) |

A verdict is **OK**, **BROKEN** (the mod does not do what the row expects) or **not shown** (the harness could
not tell). Every "no" below had a read of the same form that answered "yes" in the same session.

## Rows that failed

| Row | Result | Issue |
|---|---|---|
| Rules of War, "Game start" (`rules-of-war-playtest.md`) | **BROKEN.** Every country starts with 3 infamy, not 0: `c:USA`, `c:GBR`, `c:FRA`, `c:PER`, `c:TUR` and `c:JAP` read 3, and no country reads under 2.5. 3 is +25 − 22: Total War is the law group's first law, so it is the default at setup and is charged, and history's Traditional takes 22 back | #1595 |
| Judiciary item 6, "Shock" (`judiciary-playtest.md`) | **BROKEN.** As the USA, 16 days after `activate_law` of Executive Tribunals there was no Court Overhaul, though every part of `te_judiciary_events.1`'s trigger read true. Fired from the console the event applied it (multiplier 0.5) and raised Lawyers in the Streets. Cause, session 3: the event is queued with `days = 7` on the day the law changes, when the new ceiling is not yet in `modifier:` reads, so its trigger is false, and a delayed `trigger_event` whose trigger is false when queued never fires (the table below) | #1596 |
| `unemployment_share_read` (`ai-economy-playtest.md`) | **False BROKEN** in the fixture's run on 4 January (`state=Corsica read=0.000 exact=0.038`: the engine had computed no unemployment yet). OK on 8 January in sessions 2 and 3 (`conv=0.192 exact=0.192`) | #1597 |

**The delayed-event test (session 3, 6 February).** Both countries were seeded and neither had the modifier.
Each was sent `trigger_event = { id = te_judiciary_events.1 days = 3 }` in country scope.

| Country | Trigger when queued | Trigger on the fire day | Result |
|---|---|---|---|
| USA: on Executive Tribunals since 5 January, gap 50 | true | true | Fired: modifier on 12 February, multiplier 0.5 |
| France: queued first, then Executive Tribunals the same day (gap −35 when queued, 25 by 12 February) | false | true | Never fired: no modifier on 12 February |
| France again: queued on 12 February with the gap at 25 | true | true | Fired: modifier on 17 February, multiplier 0.25 |

## Rows that passed

| List | Row | What was read |
|---|---|---|
| Rules of War | Charge | USA, infamy after each `activate_law`: Traditional to Total War 63 to 88 (+25), once |
| Rules of War | Cut | Total War to Traditional 88 to 66 (−22); Total War to Limited War 91 to 51 (−40); Limited War to Humanitarian Regulations 51 to 56 (+5); back 56 to 52 (−4). `te_row_charged_standing` followed each law |
| Judiciary | Item 2, February scores | 9 February: Britain 70, Prussia 35, Persia 10 and the Ottoman Empire 10 with ceiling 20, USA 60. On 2 January Persia read 0: the seeding comes with the first monthly pulse |
| Judiciary | Item 6, Lawyers in the Streets | Third answer: score 60 to 70 |
| Judiciary | Item 30, `start_enactment` from an option | Ottoman Empire, "A House of Justice", first answer: `is_enacting_law = law_type:law_statutory_courts` yes. So `start_enactment` works from an event option |
| Judiciary | Self-check `judiciary_enacting_law_scope` | OK, USA, on `start_enactment` of Freedom of Conscience (a court that challenges: constitutional laws −0.1) |
| First Past the Post | Item 4, keep or drop | USA, Universal Suffrage by `activate_law`: "Counting the Votes" pending at once. Keep: amendment on Universal Suffrage. Then Wealth Voting: asked again; decline: `te_fptp_var` gone; Universal Suffrage again: no event |
| First Past the Post | Self-check `fptp_major_parties` | OK (`parties=3`, second's clout 0.28) |
| Inheritance | Item 1, The Hidden Estates, effects only | Audit: Estate Audits set, the capital's Dynastic Wealth 54.55 to 51.55, national 66.37 to 63.37. Look away: Hidden Estates set, 51.55 to 56.55 and 63.37 to 68.37. The 20-year timing was not run |
| "Told of" events | The State Collapses changes nothing | `has_modifier = failed_state_modifier` no before and after the pick. The window, picture and names were not looked at |
| Culture merges | `cm_definition_inject` | Read directly on 2 January (`cd:GER` lists `cu:north_german` and `cu:cm_german`, not `cu:french`), and the line read OK on 1 February |
| Local Climate | The modifier's size | The multiplier is read from the state: Madeira's `modifier:state_migration_pull_mult` is 0.09858 with `te_climate_bonus_applied` 9.85864, exactly ×0.01. Yakutsk −0.887 with a penalty of 63.74. Georgia's total is +0.253 with a penalty of 26.95, so other sources add about +0.52 there; the breakdown itself was not looked at |
| Local Climate | First application | 9 February: every USA state has `te_climate_base_penalty`; Georgia carries `local_climate_discomfort` |
| All-goods tariffs | Days left, grace and cooldown | Set on 6 January: 91 days left, both timed variables set. 16 January: 81, grace gone. 9 February: 57. 25 February: 41. 6 April (day 91): the cooldown variable gone, 0. So `game_date` counts days and the three months end by day 91 |
| Tourism | Agra | The Taj Mahal's state reads `tourism_bonus_from_monuments` between 0.39 and 0.60: `is_building_type` matches inside `every_scope_building` in a script value |
| 1.15.1 hotfix | Ports and railways start unsubsidized | 2 January: no country has a subsidized port or railway; ports exist and some building is subsidized |
| Vanilla 1.15 | `decentralized_law_baseline` | OK |
| Covert | `covert_can_research_current` | OK (`held=75 can_research=75`) |
| Grand Monuments | `gm_occupation_read`, `monument_piece_rejoins`, `monument_artifact_stands_apart`, `gm_world_base`, `monument_least_grandeur`, `archaeology_site_region`, `gm_education_reaches_states` | OK each. World GDP 401,621,619 against the constant's 404,100,000 |
| Cultural Hegemony | `ch_board_rows` | OK (`ranked=70`) |
| Journal map modes | `hq_found`, `hq_profit`, `banking_entry_everywhere` | OK each |
| Demographics | `primate_state_flag`, `pop_workforce_read`, `workforce_ratio_scale`, `metro_world_market_hub`, `unemployment_rate_read`, `working_conditions_read`, `famine_reserves_absorbed`, `workforce_lines_net`, `conscription_term_read`, `primogeniture_scaled`, `fl_neighbours_read`, `neighbouring_state_reads`, `measure_country_types` | OK each. `delayed_state_event` read BROKEN again, as since 2026-11-08 |

## What the runs showed about the engine

Written up in `docs/guides/scripting_best_practices.md`:

- A delayed `trigger_event` is dropped when the event's trigger is false at the moment it is queued.
- A law activated by script is not in `modifier:` reads until a day has passed.
- A law group's first law is every country's law at setup, and its `on_activate` runs then.
- `start_enactment` works from an event option, and `activate_law` from an effect fires `on_activate` and
  `on_law_activated`.

## What the harness could not do

Filed, with the rows each would open: a window over the country-select screen stops `enter-game` (#1598);
non-default game rules (#1599); adding a setup to a running session (#1600); reporting self-check lines, the
fixture run's included (#1601); fresh saves at later dates (#1602). Panels, tooltips, hovers, scripted buttons'
gates and the diplomacy screens stay with the owner's play-test: clicking GUI widgets is the harness's stated
non-goal.

Candidates looked at and not run: the power grid's unstaffed transfer station (`create_building` in a setup was
judged too easy to get wrong for a first run), the diplomatic play escalation pause (needs a play), the
homeless Cultural Renaissance (needs `remove_homeland` and a journal entry added by script) and the war of
independence's play.
