# Told of what was done to us: in-game checks

**Added 2026-11-10** with the fixes for #1554 to #1559. Each of these effects used to land on a
country with no event open and no tooltip to read. A large one now sends an event whose single
option lists what was done, under `show_as_tooltip`, and changes nothing; a small one posts a feed
notice. The offline gate (`test_told_of_foreign_effects.py`, the audits) holds the wiring. What only
the game shows is below. These checks don't gate a merge (CLAUDE.md § "In-game checks"); the
play-test before a release works through them. The anti-satellite strike's check is in
`global-commons-playtest.md` (§ 6, item 6).

Console: `event <id>` opens an event on our country, but most of these read a saved scope or a
variable their sender sets, so reach them through the real action where the table says so.

## What to look at in every one

- The event opens (as a window where the table says popup), with its picture, and names the other
  country. A blank name means the saved scope or the variable did not reach it.
- The option's tooltip lists the modifier with the same figures and time left as the modifier list
  shows on the country, and **taking the option changes nothing**: no second copy of a modifier, no
  second payment. A second copy means an effect escaped `show_as_tooltip`.

## Events

| Check | How to reach it | Expected | If not |
|---|---|---|---|
| **The State Collapses** (`minor_events_timelineextended.10`, popup) | Hold average standard of living below 4 until State Collapse's bar fills. | The event on the day of the collapse; its tooltip lists the nine buildings, the institutions and Failed State for ten years. A second collapse a year on fires it again and refreshes Failed State. | No event: the entry's pulse did not reach `trigger_event`. The window opens every week: the progress reset moved. |
| **The Assembly Rules Against Us** (`un_vote.8`) | Be the target of a carried condemnation, sanctions, each with and without a veto, and a carried motion to strip our permanent seat. Repeat as a non-member and as a member whose representation is suspended. | One event with the text for the case (condemned, rebuked, under sanctions, voluntary measures, seat lost), the vote count and the proposer; no General Assembly Vote Results (`un_vote.3`) for us on that resolution. The tooltip matches the modifiers we hold; at Strong and Supranational it adds the embargo line. | Both events: the exclusion in `un_vote.2`'s dispatch did not match us. Vote counts 0: `scope:un_resolution` did not reach the event. Under Sanctions missing from the tooltip: the target's United Nations entry is not active (`un_entry_unlocked` fails for it), and the regime's modifier is one that entry declares. |
| **Out of the Common Currency** (`te_union.2`, popup) | Adopt a bloc's common currency, then leave the bloc; and separately have the bloc lose its Monetary Union tier. | The event the month it happens, naming the leader, with the first text when we left the bloc and the second when the currency ended. Tooltip: Left the Common Currency for ten years, relations with the leader −30. Leaving by the dashboard button does not fire it. | No event after leaving the bloc: the discovery did not run that month (`te_mon_arr_scan`). Leader's name blank: `te_union_exit_from` was not set (no `te_mon_anchor`); the third text should have shown. |
| **A Currency of Our Own** (`te_inflation.2`, popup) | Dollarize in a hyperinflation, then pass any monetary-policy law. | The event when the law passes, with Currency Reform for ten years in the tooltip. Entering a Command Economy instead fires nothing. | The event at the start of enactment instead of at passage: note it; the text says "is in force". |
| **Blesses / Forbids the Union** (`irredentism.12`, `.13`) | As a bloc leader, answer A Sister Asks to Be Absorbed (`irredentism.8`) each way; watch as the member and as the proposer. | Both countries get the event a day later, each with its own text; the forbidden member's tooltip shows Bloc Leader Forbade Union for five years. | Only one country: the other's saved scope was gone. The proposer's text on the member: `this = root` in the `first_valid` did not match. |
| **The Summit's Communiqué** (`te_pb_summit.2`) | As a member of a bloc whose AI or human leader takes an identity initiative that reaches every member (joint exercises, a council of the faith, customs, a congress, a cultural congress, a conference of ambassadors). | One event a day after the summit, naming the leader and the initiative, with the ten-year modifier in the tooltip. The leader gets none. | The wrong initiative's text: an older `<modifier>_told` variable was still set. No event: `<modifier>_told` was not set (`name = $MODIFIER$_told` did not substitute). |
| **An Answer on Reparations** (`nuclear_weapon_events.33`, popup) | Be struck by a launch the striker says was unordered, hold back our answer and demand reparations; have the striker pay, then in another game refuse. | The event with the sum paid (matching what our treasury gained) or the refusal, and relations +20 or −30. | Sum 0: `nd_claim_paid` was read before it was set. |

## Notices

| Check | How to reach it | Expected | If not |
|---|---|---|---|
| **The Decolonization Declaration** | Hold an overseas colony when the Decolonization Resolution carries, as a member and as a non-member. | One feed notice naming the modifier; none if we already held it. | |
| **The UN Headquarters Comes to Us** | Be the great-power member picked when the host leaves the United Nations. | One feed notice; the founder gets none at the founding. | |
| **Blocs Fill the Vacuum**, **The Blocs After the United Nations** | Lead a power bloc when the United Nations turns Moribund, and when it dissolves. | One notice each time the bloc gains the modifier, not one a month. | One a month: `has_modifier` on the bloc does not see the modifier the pulse added. |
| **Swap Line Called In / Repaid** | Draw on a swap line in a crisis, then end the treaty with a balance outstanding. | A notice to each side with the same sum, equal to the balance the dashboard showed. | Sum 0: the notice read `te_mon_swap_settled_amount` from the wrong country. |
| **Cultural Ties Funded** | Be the neighbor a same-culture country funds ties with (`irredentism.1.b`). | A notice naming the funder, relations +15 and the modifier. | |
| **Another Operation Exposed**, **Anger at Foreign Friends** | Have two operations against us exposed within two years; and order a response at the catch against a country a lobby of ours favors. | The second exposure posts Another Operation Exposed in place of the event; Anger at Foreign Friends follows whenever our lobby's interest groups took Foreign Ties Discredited and the event was not shown. | The operation's name blank: the exposure record was read before `covert_op_burn` wrote it. |
| **A colonial subject's liberty-desire modifiers** | As a colonial subject of an empire whose Colonial Stability is below 65, hover Restless Colonial Subject (or its two stronger forms) in our modifier list. | The description names the empire's Colonial Stability and the threshold. | |

## Harness run, 2026-11-11 (1.15.1)

Run through `python3 -m game_qa` on a fresh 1836 game; figures and run folders in `docs/testing/game-qa-results-2026-11-11.md`.

The State Collapses: taking the option adds no Failed State (read before and after). The window, picture and names were not looked at.
