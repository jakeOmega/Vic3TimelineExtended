# Treaty article Involvement play-test checklist

What the next play-test should look at in the Involvement the mod's treaty articles build (2026-11-03). In-game checks
do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and
adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through
with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** An article's tooltip in the treaty draft (the Involvement line reads "Increases the Involvement of
  … by a maximum of N in all strategic regions where … is local"), and a strategic region's interest-tier tooltip, whose
  "Involvement is due to" breakdown lists each treaty.
- **Logs.** Read `debug.log`, not `error.log`.

## Which side gains (the load-bearing assumption)

`target_involvement_applies_to` is read as naming the **local** side, the other party gaining (vanilla's investment
rights and guarantee only make sense this way). Values and reasoning: `docs/systems/mod_systems/treaties.md`
§ Involvement; offline, `treaty_leverage_side_audit` holds every article to that rule. **Fallback for the whole list:**
if the gainer comes out backwards, flip every directed article's `target_involvement_applies_to` (source ↔ target) and
the audit's `wrong_side` rule with it (`_BLOCK_SIDE` and the maintenance branch in `_judge_involvement`).

| Check | Expect | If it fails |
|---|---|---|
| **Aid.** Draft Education Aid as the donor; read the article tooltip. | The donor gains up to 1,000 where the recipient is local. | The recipient named as gainer: apply the fallback above. |
| **Peg.** Draft a Currency Peg (we peg to a larger economy); read the tooltip. | The anchor gains up to 2,000 where the pegger is local. | As above. |
| **Request Influence.** Ask a bloc leader for influence. | The bloc leader gains up to 2,000 where we are local. | As above; this is the one article whose maintenance payer is also the local side. |
| **Mutual.** Draft a Cultural Exchange Program. | Both countries gain up to 1,000 where the other is local. | A one-sided line means the engine ignores `mutual` on a mutual article: compare with vanilla's alliance. |
| **Breakdown.** Sign Extend Influence with a regional power; after a few months open that region's interest tier tooltip. | The treaty appears in the Involvement breakdown, and current Involvement climbs toward the target. | Nothing listed: the field may need a game restart, or the article type isn't read; check `debug.log` for the article. |
| **None.** Draft Seize Company or a Demilitarized Zone. | No Involvement line. | Cosmetic, but the reviewed reason no longer holds: remove the tag and give it a figure. |
| **Cap.** A donor with five or six aid articles to one local power. | Treaty Involvement in that region stops at 5,000. | Record the figure; the cap is vanilla's `INTEREST_TREATY_PACT_INVOLVEMENT_CAP`. |

## Pacts (2026-11-12, #1380)

The mod's pacts copy their nearest vanilla analogue's pair exactly (`docs/systems/mod_systems/treaties.md`
§ Involvement, **Pacts**), so they read as vanilla's whichever side `source_country` names. The checks confirm the
fields are read on a mod pact at all and settle the side for the player guide's wording, which says the initiator
gains where the target is local.

| Check | Expect | If it fails |
|---|---|---|
| **Vanilla first.** Hover Fund Lobbies on a country with a lobby. | An Involvement line naming the funder as gainer where the target is local. | Record the wording: it settles the side for pacts. If the target gains, reword the guide's three sentences (`09-diplomacy.md`, `11-influence.md`); the script stays as vanilla's. |
| **Covert.** Launch Cultivate Assets (any target not your subject); hover the action and, after a few months, the target's region interest tier. | The same Involvement line as Fund Lobbies, up to 1,000; the operation listed in "Involvement is due to". | No line: the fields are not read on this pact; compare with Humanitarian Aid and record which pacts show one. |
| **Aid.** Give Humanitarian Aid (Welfare IV bloc principle). | As Increase Relations: up to 1,000. | As above. |
| **None.** Hover Lobby For the Resolution on an AI UN member. | No Involvement line. | Cosmetic; the reviewed reason no longer holds. |

## Activism and turmoil in the AI's answer (2026-11-15, #1829)

Six tests in the AI's acceptance scores compared fractions against whole percentages (activism and turmoil run 0 to 1), so they never applied. They read 0.25, 0.5 and 0.75 now (`docs/systems/mod_systems/pops_and_migration.md` § Population Transfer, `treaties.md` § AI demand weights). Nothing here rests on an unread engine fact.

| Check | Expect | If it fails |
|---|---|---|
| **Population Transfer.** Demand one from an AI country that hosts a cultural minority movement of one of our primary cultures at 25% activism or more. | The AI's answer lists "from cultural tensions" (+25), or "from severe cultural unrest" at +50 above 50% and +80 above 75%. | No line: read `political_movement_radicalism` on that movement in the console and record it. |
| **Aid and turmoil.** Offer Crisis Resolution or Security Aid to a country with a state above 25% turmoil. | The score lists "from turmoil in target country" (+20; +15 for Development Assistance). | As above, with the state's `turmoil`. |
