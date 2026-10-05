# UN votes: later AI ballots, visible leans, and lobbying

Status: design approved by the owner in conversation on 2026-09-27; this spec
awaits the owner's review. No implementation yet.

## Goal

Give players a real chance to react to how the AI will vote on a UN resolution.
Today every AI member computes its lean and casts its ballot in the same moment,
30 days after the resolution opens, so nothing can be shown or influenced before
it votes. After this change:

1. AI members vote late in the session, at a random month between 9 and 11.
2. Each AI member's lean is visible, as an imperfect reading, from the first
   month.
3. Any member can try to move an AI member's vote, in either direction: a cheap,
   gradual influence campaign, or an expensive, binding pledge paid with an
   obligation.
4. The AI lobbies too, so outcomes cannot simply be bought.

Uncertainty is a feature: the displayed lean is a reading, not the number, and a
close vote can still turn on the casting roll or on a member voting before your
campaign has moved it.

## Owner decisions (2026-09-27)

| Question | Decision |
|---|---|
| Who may sway a vote | Any UN member, for or against (the owner's first thought was proposer-only; "a is better if we can") |
| Precision | Imperfect information is preferred |
| Small sway | Costs influence: a lobbying campaign with weekly upkeep whose effect builds each month |
| Big sway | Costs an obligation: a pledge, which the member can refuse |
| When AI members vote | Staggered, never before month 9 ("bad luck can impact you if it is a close thing") |
| AI lobbying | Yes, both ways |
| Chamber rows | Persuadable members first; firmly decided members summarised |
| Campaign mechanism | A diplomatic pact |
| Numbers | The designer's first-pass values; tuned by playtesting |
| Human vote event | Needs a "decide later" option |
| Pledged against | Votes no, but still vetoes if it would have vetoed anyway |

## How it works today (facts, origin/main 5d18ac08)

- **The resolution** is a script container (`common/scripted_effects/un_vote_effects.txt:4-47`) with the lists `un_res_yes` / `un_res_no`, the tallies, `un_res_months`, and `un_res_ai_cast`. One resolution at a time (`un_vote_active`).
- **Opening** (`un_resolution_open`, `un_vote_effects.txt:68-132`) queues `un_vote.1` (the human vote popup) to human members at 30 days, `un_vote.5` (AI dispatch) at 30 days and `un_vote.2` (decision) at 365 days to the proposer, and writes human leans at once.
- **AI ballots**: `un_vote.5` → `un_vote_dispatch_ai_ballots` (`common/scripted_effects/un_dossier_effects.txt:194-208`) fires the hidden `un_vote.4` to every AI member, which runs `un_lean_snapshot` then `un_vote_ai_cast` in the same `immediate` (`events/un_vote_events.txt:1797-1830`). A monthly fallback dispatches after 2 months (`un_vote_effects.txt:398-411`).
- **The lean** is `un_vote_lean` (`common/script_values/un_dossier_values.txt:700-712`), a sum of terms evaluated with ROOT = the voter (relations read `relations:root`), so it can only be computed inside an event fired to that voter. Casting adds a roll of −20/−10/0/+10/+20 (`un_vote_ai_cast`, `un_dossier_effects.txt:166-187`). Veto rule: `un_vote_ai_should_veto` (`common/scripted_triggers/un_dossier_triggers.txt:56-77`).
- **Human leans** are refreshed monthly (`un_vote_refresh_human_leans`, called at `un_vote_effects.txt:409`) and shown only to the viewer (`un_chamber_position_sgui`).
- **The chamber** (`gui/journal_entry_widgets/un_chamber_widget.gui`) renders everything as scripted-GUI tooltips (`common/scripted_guis/un_chamber_sguis.txt`, `common/scripted_effects/un_chamber_display_effects.txt`). The recorded ballot is one text block over the yes/no lists. PR #453 introduced per-row slots with an `op` argument for missions (0-7) and the archive's voting details (0-29), because within one tooltip the engine gathers all of a country's lines under its first appearance (gotcha #27).
- **Voting**: humans can vote from day 1 through the chamber (`un_chamber_vote_sgui`) and can never change a vote (`un_vote_can_cast_ballot`, `common/scripted_triggers/un_resolution_triggers.txt:101-110`). The popup `un_vote.1` forces a choice.
- **Existing lobbying**: Seek a Vote Commitment (`common/diplomatic_actions/un_lobbying.txt:46-316`, effects `common/scripted_effects/un_lobby_effects.txt`): proposer only, yes only, two per resolution, costs an obligation owed to the recipient, adds a +100 lean term (`un_lean_pledge`), kept/broken bookkeeping with standing and relations effects.
- **Base-game pacts**: Improve Relations is a one-sided pact with `cost = 150` influence maintenance (`game/common/diplomatic_actions/00_relations_actions.txt:23-30`); `create_diplomatic_pact` / `can_create_diplomatic_pact` exist as script effect and trigger.

## Design

### 1. Timing and leans

- **Casting month.** When a resolution opens, each AI member draws its casting month, 9, 10 or 11 (one in three each), stored as a variable on the voter tied to the resolution (like `un_lean_res`). The monthly UN update casts, for each AI member whose drawn month has come, using its current lean plus the existing ±20 roll. At the final tally (`un_vote.2`), any AI member that has not voted (for example, one that joined late) casts first. `un_vote.5` stops dispatching ballots; the two-month fallback is replaced by the monthly casting check.
- **Lean snapshots.** From day 30, each AI member's lean is computed monthly by a hidden event fired to it (the lean needs ROOT = the voter), reusing `un_lean_snapshot`. `un_vote.4` is split: snapshot only, and a separate cast step. A member that joins mid-session gets a snapshot at the next refresh and a casting month of the later of its draw and next month.
- **Displayed band.** The chamber shows a band, not the number:

  | Band | Lean |
  |---|---|
  | Firmly for | +30 or more |
  | Leaning for | +10 to +29 |
  | Undecided | −9 to +9 |
  | Leaning against | −10 to −29 |
  | Firmly against | −30 or less |

- **Misreading.** Each AI member draws a fixed misreading of −10, 0 or +10 once per resolution; the displayed band uses lean + misreading. While the viewer runs a campaign on that member, the viewer sees the true band.
- **Casting uses the true lean** (plus the roll), never the misreading.

### 2. The human vote event

`un_vote.1` gains an option "Decide later" that closes the event without voting and re-queues it at month 9 and again at month 11 (not after the member has voted). The chamber's vote buttons stay available throughout. The existing default option stays as is.

### 3. Lobbying campaigns (a diplomatic pact)

- **Two one-sided pacts**, "Lobby for" and "Lobby against", from the lobbying country to an AI UN member. Valid while a resolution is in session, the member has not voted and is not the resolution's target, and both are members with a vote. Not usable on human members (humans decide for themselves).
- **Cost**: influence maintenance near the base game's Improve Relations (150), scaled by the member's rank where the engine allows: about 75 for minor powers, 100 for major powers, 150 for great powers. If the pact `cost` does not accept a script value, one flat cost of 100.
- **Effect**: each full month a campaign runs adds 3 lean toward its direction, up to 15 per campaign. Campaigns in the same direction stack to at most 20; opposing campaigns net out. The accumulated shift is a new lean term (for example `un_lean_lobbying`) read by the monthly snapshot and at casting.
- **Ending**: the pact ends when the member votes or the resolution closes (lapse, decision, veto), and can be cancelled at any time; cancelling frees the influence and drops that campaign's accumulated shift.
- **The chamber row buttons** create or cancel the pact (`create_diplomatic_pact`); the pact also appears in the diplomacy panel like any other.

### 4. Pledges

- **Seek a Vote Commitment** opens to any member, in either direction, until the member votes: two actions, "pledge for" and "pledge against".
- **Cost and acceptance** stay as today: an obligation owed to the member, and the existing acceptance score, with its target-ties terms flipped for "against".
- **Effect**: a pledge for adds +100 lean and a pledged permanent member never vetoes (today's rule). A pledge against adds −100 lean; the member votes no, **unless it would have vetoed anyway**, in which case it still vetoes. A pledge against can never be used to prevent a veto.
- **Limits**: one pledge per member per resolution (first accepted wins); each country may collect up to two pledges per resolution.
- **Broken pledges** by humans keep today's penalty (standing and relations with the country that asked, obligation struck off).

### 5. AI behaviour

- **The proposer** lobbies for: campaigns on AI members whose true lean is undecided or leaning against, up to three at once, only while its influence surplus covers the cost with a margin; and pledge requests to members close to the line.
- **The resolution's target, its allies and its bloc leader** lobby against in the same way.
- **The AI never runs campaigns on human members**, but may ask humans for pledges (as today, with the engine's accept/decline).
- **Accepting pledges** uses the adapted acceptance score.

### 6. The chamber display

- **A Delegations section** under the resolution in session, with up to 24 member rows built with the per-row slot pattern from PR #453 (one scripted-GUI tooltip per row, so gotcha #27 cannot merge rows).
- **Order**: members with a campaign or pledge first, then undecided, then leaning for, then leaning against. The order is built into a variable list at each monthly refresh.
- **Each row**: the member's name, displayed band, who is lobbying it and which way, any pledge, its vote once cast; buttons Lobby for, Lobby against, Seek pledge (each greyed with a reason when invalid).
- **Summary line**: counts of firmly-for and firmly-against members not shown in rows, with a tooltip listing them; and a count of members that have already voted.

## Old saves and edge cases

- A resolution open when the save is loaded: members without a casting month draw one at the next monthly update (at least next month); members that already voted keep their vote.
- The one-resolution lock, the 14-month lapse, topic cooldowns, the recess, Article 19 and suspended representation are unchanged.
- The supermajority count still counts non-voters against; staggering does not change who is eligible.
- The Charter Reform II veto override is unchanged.
- Revolutions: a civil war's winner inherits variables but not variable lists or pacts (CLAUDE.md). Campaigns are pacts, so they end; the implementation plan must settle how a winner's casting month, misreading and pledges carry over under the mod's rule that the winner continues the nation.

## Risks to check before building

1. Whether a pact's `cost` accepts a script value (for rank scaling).
2. Whether `create_diplomatic_pact` works from a scripted-GUI effect for a one-sided pact, and whether pacts can be ended by script (`remove_diplomatic_pact` or equivalent) when the member votes.
3. The monthly per-AI lean event: its cost with 60+ members; acceptable if it runs only while a resolution is in session.
4. Building the ordered row list in script without sorting primitives (grouped passes into one list).

## Testing

- Python tests pinning the structure: the casting-month draw and monthly casting path, the split of `un_vote.4`, the two pacts' validity and end conditions, the lobbying lean term and its caps, the pledge direction and veto rule, the "Decide later" option, and the row slot count.
- The CI audits (`prev_scope`, `silent_variable`, `container_timed_variable`, `je_immediate_reset` and others) must pass; lists live on the resolution container, as today.
- In-game checks: leans visible from month 1; no AI vote before month 9; a campaign's effect over months; a refused and an accepted pledge; a permanent member pledged against still vetoing; the AI running campaigns on both sides; "Decide later" returning at months 9 and 11.

## Player guide

The UN chapter (`10-united-nations.md`) changes: when members vote, reading leans, campaigns, pledges in both directions, the "Decide later" option, and the AI's lobbying. Update it in the implementation PR (see CLAUDE.md, "Keep the player guide current").

## Out of scope

- Changing the lean formula itself.
- Lobbying on the resolution's target, or campaigns aimed at human members.
- More than one resolution at a time.
