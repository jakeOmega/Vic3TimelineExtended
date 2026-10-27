# United Nations tooltips play-test checklist

What the next play-test should look at in the UN panel's tooltips. In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The United Nations journal entry, or the UN tab of the Diplomacy panel: the overview's agency
  icons, the General Assembly's Table a Resolution rows, the resolution in session, and Our Obligations.
- **Quick setup.** `event te_debug_un.1` founds the UN and seats the great and major powers, and can have another member
  table a condemnation (`events/te_debug_un_events.txt`).
- **Logs.** Read `debug.log`, not `error.log`. Search it for `Failed parsing localized text`, `je_un_terms_` and
  `je_un_ov_agency_`.

## Every topic's terms, on four surfaces (2026-10-16)

Each topic has one terms text, `je_un_terms_<topic>`, shown in four places (docs/systems/journal_entry_systems.md,
"Terms tooltips"). Two of the four rest on patterns that are proven separately but not in this combination: a
`tooltip = "<key>"` whose loc carries a `SelectLocalization` and several `GetStaticModifier(...).GetDesc` lists, and a
tagged hover (`#tooltippable;tooltip:[GetPlayer.GetTooltipTag],<key>`) on a proposal row's title.

| Check | Expect | If it fails |
|---|---|---|
| **Agency icons.** Hover UNESCO, the IAEA and the ICJ in the overview, before and after they are founded. | The agency's name, "Founded." or "Not yet founded.", then its convention's terms with each modifier's effects listed. The ICJ says it has no effects of its own. | A blank or raw tooltip means the direct loc key does not render `SelectLocalization` there: go back to `Concatenate( Localize(...), SelectLocalization(...) )` in `gui/journal_entry_widgets/un_overview_widget.gui` for the name and status, and give the terms a second line. |
| **Proposal titles.** Hover the title of a convention (Cultural Heritage Program), a member topic (Condemnation of Aggression) and a reform in Table a Resolution. | The topic's terms, each modifier's effects, the shared outcomes and, for a convention, when the docket raises it. | Plain text with no effect lists means the tagged form failed on that row; a raw `je_un_chamber_propose_topic_*_tt` means the hover key did not resolve. |
| **The card.** With a resolution in session, hover **Its terms** at the end of the If it carries line, and again after a veto. | The same terms, with the shared outcomes under them. | A word that does not hover: check `je_un_chamber_conseq_<tag>`. |
| **Our Obligations.** As a party to a convention, hover its name. | Its full terms, not only the member modifier. | Only the member modifier means the old `je_un_chamber_conv_<key>_tt` loaded from a stale copy (search `te_unused_l_english.yml`). |
| **Length.** Hover the longest: Decolonization Resolution, Request a Peacekeeping Deployment, Charter Reform II. | The tooltip fits the screen at 1080p. | Too tall: move the shared outcomes (`$je_un_terms_common$`) off the proposal titles and keep them on the card only. |
| **UNESCO in play.** With UNESCO in force, occupy a state with a Grand Monument and carry it off. | The infamy the trophy row shows is twice the figure without UNESCO, matching the agency's tooltip. | A mismatch means `gm_trophy_values.txt` and `je_un_terms_heritage` disagree: `test_un_terms_tooltips.py` should have caught it. |

## What a carried resolution does to the members (2026-10-16)

The same PR fixed seven things the terms audit found the script doing against its own design
(`test_un_vote_consequences.py` pins each offline). What only the game shows:

| Check | Expect | If it fails |
|---|---|---|
| **A held veto.** Vote against a sanctions resolution, have a permanent member veto it, and let it carry in its voluntary form. | `un_vote.3` says the veto left nothing binding; Accept shows no standing gain, and Denounce shows relations and infamy but no standing loss or defiance record. | A standing line means `un_res_vetoed` was gone by `un_vote.3`: check where `un_vote_effects.txt` removes it. |
| **Peacekeeping pledges.** As a major power in the Peacekeeping programme, refuse a carried full deployment; as another, pledge to one. | The refuser's End Peacekeeping button stays as it was; the pledger gains Peacekeeping Commitment Active (one copy) and cannot end the programme for ten years. | Two copies of the commitment mean the remove before the add in `un_vote_apply_resolution_compliance` did not take. |
| **Bloc leverage.** As a bloc leader, vote for a peacekeeping request that a veto cuts to observers. | No +50 leverage over the requester. | Leverage means the limit in `un_vote_apply_resolution_compliance` lost `un_resolution_peacekeeping_full`. |
| **Sanctions against us.** Be the target of sanctions and vote for them. | When they carry, the proposer gets no Sanctions Enforcer modifier and can table sanctions again. | An enforcer modifier means `un_res_target_accepted` was not set on the resolution: check `un_vote_cast_yes`. |
| **Expulsion, mandate or referral against us.** Vote for it as its target. | The option reads as an ordinary vote in favour, and no Self-Corrected modifier appears. | "We accept the resolution." means `un_vote.1` option A's name does not read `un_resolution_target_may_accept`. |
| **Decolonization pressure.** Hold an overseas colony when the declaration carries, having cracked down on intellectuals beforehand. | Both Anti-Colonial Backlash and Decolonisation Declaration: International Pressure, each with its own description. | Backlash alone means `un_vote.2` still reads the crackdown's modifier. |

## Lifting sanctions (2026-10-16)

The petition to lift sanctions and the regime's monthly upkeep (docs/systems/un_redesign_design.md §0.12a). Found the
UN with `event te_debug_un.1`, then have a major power table International Sanctions against a rival whose case
strength is 50 or more, and let it carry.

| Check | Expect | If it fails |
|---|---|---|
| **The row.** Under sanctions, open Propose a Resolution. | Lift the Sanctions Against Us shows the enforcer's name and the months in force, and tables. Not under sanctions, it says No Case. | A blank name: `je_un_chamber_propose_preview_lift_sanctions` lost `scope:un_lift_sanctions_enforcer`; check `un_lift_sanctions_chamber_preview`. |
| **A carried petition.** Let one carry. | The modifier and the Assembly's embargoes are gone, and the enforcer's Propose Sanctions row opens again. | The enforcer still blocked: `un_sanctions_lift_regime` did not reach `var:un_sanctions_enforced_by`. |
| **A veto.** Petition against an AI permanent-member enforcer, once while it is your rival and once after the rivalry has ended and relations are above Cold. | It vetoes the first and not the second; a vetoed petition says it was blocked and the sanctions stay. | A veto in the second case: `un_lift_sanctions_ill_disposed` is missing from `un_vote_ai_should_veto`. |
| **An orphaned regime.** Have the enforcer leave the UN. | The next month the sanctions lapse, with The Sanctions on Us Lapse in the feed. | Still sanctioned: check `un_sanctions_regime_orphaned` on the target. |
| **A revolution.** Let a revolution win in a sanctioned country. | The winner is under the sanctions again within a month. | |

## Proposal durations (2026-10-23)

`add_modifier` reads a duration given as a script value written as a block, or computed, as 0 days: Planned Capital's
option said "for 0 days" (`scripting_best_practices.md`, "Modifier & Cooldown Duration Units"). The proposal pace's two
marks were computed and the sponsor's cost a `{ value = 730 }`. The marks are now a ladder of literals over
`un_propose_pace_mult` (`un_propose_add_sponsor_mark`, `un_propose_add_request_cooldown`), the cost a bare
`un_sponsor_cost_days = 730`, and `modifier_duration_audit` keeps the form out. The World Court's two windows are
`set_variable` lifetimes, made bare too though that form was never seen to fail.

| Check | Expect | If it fails |
|---|---|---|
| **Own motion.** As a Neutral member that is not a great power, hover Propose on a convention row (Cultural Heritage Program) in Table a Resolution. | General Assembly Resolution Participant for 1825 days, UN Request Cooldown for 3650 days, Sponsoring a UN Resolution for 730 days. | "for 0 days" on the cost: a bare script value reads as 0 as well; write `730` in `un_propose_sponsor_cost`. Every rung listed: the tooltip shows each `else_if`; wrap each ladder in a `custom_tooltip` naming the duration. |
| **The pace.** The same as a great power at Respected, at Exemplary, and as an ordinary member at Disgraced. | 776 and 1551 days; 639 and 1278; 2738 and 5475. | The wrong rung: compare `un_propose_pace_mult` with the bands in `un_propose_effects.txt` (`test_un_propose_pace.py` checks the arithmetic). |
| **The docket's appeal.** `un_events.2`, An Appeal to the Assembly. | The condemnation option shows General Assembly Resolution Participant for the pace's days; the sanctions option shows it and UN Request Cooldown. | As above. |
| **They run.** Table on our own motion, then look at the country's modifiers a month later. | Both marks are there and expire about five and ten years on (less for a great power); a second own-motion proposal stays greyed until the cooldown ends. | Gone at once or never expiring: report it, with the modifier's expiry from the tooltip. |
| **The World Court's windows.** Have a ruling defied, and another found for the holder. | A year on, the claimant may still move for a military mandate over the region without the case of 60 (ten years in all), and a war goal against the region still costs it extra infamy (twenty). | Gone at once: `set_variable` reads a bare script value as 0; write `3650` / `7300` at the four sites in `un_justice_effects.txt`. |

## A motion to expel weighed on its own case (2026-10-24)

A motion to expel no longer carries on the habit of consensus: every member but the target adds the case for expulsion
(veto record, less standing and service) to its lean, and a proposer next in line for the seat costs it 5
(docs/systems/journal_entry_systems.md, "Expulsion Vote"). Quick setup: `event te_debug_un.1`, then veto a binding
resolution as a permanent member.

| Check | Expect | If it fails |
|---|---|---|
| **Our Record.** After the veto, open Our Record (and again as a member that holds no seat: no block). | An Our Permanent Seat block: Veto record 5, and Case for expelling us with our standing and service; its hover lists the three parts with numbers. | No block: the `un_disp_veto_record` row's `visible` failed. A hover with raw `[JournalEntry...]` text: the row tooltip has no journal-entry context; move the figures into the row's own text. |
| **The record fades.** Twelve months on. | About 4.75. | Unchanged or gone: check `un_veto_record_monthly_update` runs from `un_dossier_monthly_update`. |
| **The propose row.** As another great power with no seat, open Table a Resolution. | Motion to Expel names the vetoer with the strongest case and shows Case for expulsion with its parts; when we are the great power with the most prestige that holds no seat, also The seat: we are next in line. | The seat line never shows, or shows for a power that is not first: `un_expulsion_next_in_line` (`prestige > prev.prestige` in an `any_country`) misread; compare the Security Council's in-line list. |
| **The vote.** Table it, then read our lean under the resolution and the Delegations list. | The habit of consensus reads +0 (none on a motion to expel); the case against the target equals the case shown when tabled; a proposer next in line reads 5 less in "ties to the proposer". A neutral Assembly against an Exemplary vetoer that hosts the headquarters leans against. | Consensus still +10: `un_lean_consensus` did not read the topic. The grounds line's "stood at" equal to Our Record's Case strength (never negative) instead of the case for expulsion: `un_resolution_open` could not read the new container's tag; set `un_res_case` in `un_propose_expulsion_effect` instead. |

## The panels after the GUI audit (2026-10-27)

The UN slice of the 2026-10-27 GUI and localization audit (docs/audits/gui_audit/un.md, UN-1 to UN-26). Every journal
entry button is the AI's now (`is_ai = yes` in its `visible`, Banking's pattern), and a human acts through scripted
GUIs that mirror the buttons word for word (`common/scripted_guis/un_action_sguis.txt`, `test_un_actions.py`). Quick
setup: `event te_debug_un.1`, and play a major power. No item here rests on a script fact a `TE_SELF_CHECK` line could
check: each is about what the panel draws.

| Check | Expect | If it fails |
|---|---|---|
| **The AI still acts.** Run five years as an observer. | AI members join, withhold and pay dues, join programs and champion or undermine the order as before: the counts in Programmes and Conventions and the champions list move. | Frozen counts: `is_ai = yes` hid the buttons from the AI as well; check `je_united_nations.txt`'s buttons against `banking_alt_economy_buttons.txt`. |
| **No grid for us.** Open the journal entry as a human. | No button grid under the entry; the UN tab has no Actions section. | A grid: a button lost its `is_ai = yes` (`test_un_actions.py` should have failed). |
| **The overview cells.** Before founding, as a member, during a vote and after voting. | Membership with Found, Join or an armed Leave under it (Leave asks Confirm or Think Again); the session cell says Vote due in red, then Voted for or against; Our Motions says how many are ready or the months to wait; the words are not cut off. | A blank cell: its display code (`un_overview_display_values.txt`) is never set; an elided word: shorten it (`test_un_widths.py` budgets at 8.6 a character). |
| **The inline controls.** Hover a greyed Withhold Our Dues, Pledge Grain, Fund Development, Champion the Order and a programme's Join. | The requirements as requirements (ticks and crosses), then what pressing does, with the modifiers as coloured lines. | Prose instead of modifier lines: the scripted GUI's `effect` tooltip does not print an unwrapped `add_modifier` on the journal entry; wrap it back in `custom_tooltip` with `[GetStaticModifier(...).GetDesc]`. |
| **Our ballot.** With a resolution in session, before and after voting. | Our vote line under the tally, the vote buttons under it, our lean on one row with its terms on hover. | |
| **The proposal list.** Open Propose a Resolution with a convention in force and one topic with a case. | The heading says "(1 ready)" after the next monthly update; the topic is under Ready to Table, the rest under the collapsed No Case Now; the convention in force is in neither, and the intro counts it. A targeted topic with no case names the nearest candidate and the case it needs. | Rows in both lists or neither: `un_chamber_propose_ready_sgui` / `_shelved_sgui` did not receive `op` through `IsValid`. |
| **Our next motion.** Table on our own motion, then look a few months later. | The intro says "Our next motion: in N months", counting down month by month; the overview's Motions cell agrees. | Stuck: `un_propose_wait_monthly` did not run from the entry's pulse. |
| **The mandate from Our Case.** Hold a claim on a state of a country whose case is 60 or more. | Mandates in Force › Our Case has Propose the Mandate, greyed with the same reasons as the list's row. | |
| **Missions.** With a peacekeeping mission in the field, as a major power and as a minor one. | Each row has a progress bar with Month N · ×strength beside it; Send a Contingent hides on an electoral mission and on our own, and a minor power sees one line, "We can send no contingent: …", and no buttons. | A bar at 0 on a mission with progress: the slot's `un_disp_msn_slot_<N>_frac` reads no mission; check `un_mission_in_slot`. |
| **Delegation flags.** A month into a vote. | Each Delegations row starts with its member's flag. | No flags: the mirror (`un_deleg_mirror_flags`) did not run from `un_vote.7`, or `Var('un_deleg_cap_<N>').GetState.GetCountry` does not resolve here as it does for the Security Council's seats. |
| **The archive.** Open Resolutions on the Record. | One row per resolution, newest first, its title and how it ended; the rest of its card on hover. Voting Details still lists the ballots, without the pledge caveat on each. | A blank hover: `un_chamber_history_card_row_sgui` did not receive `op` in a tooltip. |
| **Type sizes.** Look at the panels at 1080p. | Rows, buttons and notes at 17, subheadings at 20, the overview at 16; nothing elided. | |
