# Event text rewrites: in-game checks

The event text rewrites (#1539) change wording, and now and then a description's gating. The offline checks cannot show how the new flavor forms render. Each batch adds its rows here; the play-test before a release works through them.

Fire an event from the console with `event <id>` (debug mode). An event fired this way skips its trigger, so its scopes may be empty: a blank party name there is the console's doing, not the text's.

## What to look at in any rewritten event

| Check | Expected | If not |
|---|---|---|
| A list flavor (a heading line, then one item to a line) | The heading, a blank line, then each item on its own line, none running into the next | The `\n` breaks are not rendering in the flavor box: join the items into a paragraph with semicolons, or change the form |
| A document flavor ("To the ..., from ...") | Reads as one paragraph; no stray quotation marks | Check the key for an unescaped `"` |
| A long flavor (over about 120 words) | Fits the event window without the options being pushed off or the text scrolling | Cut to the guide's 150-word ceiling or below |
| A real quotation with its attribution | The quotation, then `— Name` on its own line | The `\n` before the dash is missing |

## Elections (`modern_election_events`, #1540)

| Check | How | Expected |
|---|---|---|
| The list form renders | `event modern_election_events.15`, `.28`, `.30` | As the first row above |
| The gated description | With Universal Basic Income enacted, `event modern_election_events.29` | The description opens "Universal basic income is already law in ..."; without the law, "Universal basic income has become the most argued-over proposal ..." |
| The live figure | `event modern_election_events.3` with Global Warming on | The description shows the world's temperature anomaly as a number with °C, not `0` or a raw key |
| The one-line quotation | `event modern_election_events.19` | "The medium is the message." with its attribution beneath |

## Space race landing reports (`space_race_events.3`, `.7`)

| Check | How | Expected |
|---|---|---|
| Each option reads as said after the landing | `event space_race_events.7` after choosing each approach in `event space_race_events.83` (and once with none chosen); `event space_race_events.3` with the Sea of Tranquility and far side sites from `.5` | One option, matching the approach or site, in the past or present tense; the two-sentence orbital line fits its button |
