# Seize Strait war goal play-test checklist

What the next play-test should look at in the Seize Strait war goal (`te_seize_strait`, 2026-11-07). In-game checks do
not gate a merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and
adds what only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through
with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **A quick case.** Start in 1836 as Spain (Britain holds Gibraltar as a one-province state) or as Siam or Johore
  (Britain holds Singapore as a three-province state in Malaya); Siak holds the Sumatran shore of Malacca as part of
  North Sumatra. Open a play against the owner and look for Seize Strait among the goals.
- **Logs.** Read `debug.log`, not `error.log`. Each enforcement writes one `TE_SELF_CHECK OK|BROKEN te_seize_strait`
  line with `shores=before->after` (the shore provinces the holder owns in the strait's state region),
  `holder_pop=before->after target_pop=before->after` for that region and `ai=0|1`. A goal whose state changed hands
  first (an annexation ran before it) writes `TE_SEIZE_STRAIT skipped` instead.

## Self-checks

| Line | OK means | If BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK\|BROKEN te_seize_strait` | The holder owns more of the strait's shore than before the transfer. Owning land in the region isn't enough: Spain at Gibraltar and Johore or Siam at Singapore already do. | If the map shows the shore moved, `set_owner_of_provinces` takes effect after the effect block: move the after-reading to a day later. If nothing moved, `debug.log` has a script error on `te_seize_strait_shores`, or a `this = p:xHEX.state` test is false for a province the state holds. |

## First release (2026-11-07)

| Check | Expect | If it fails |
|---|---|---|
| **Offered.** In a play against a country holding a shore state, open the war goal list. | Seize Strait is listed for that state, not for its other states, and not for a canal zone whose canal isn't built. | Not listed at all: first look in `debug.log` for a `Wrong scope` line on `te_seize_strait_shore_provinces` (the shore test is `this = p:xHEX.state`, as in the base game's Macao decision; the province iterators don't run from a state). If there is none, the custom kind with `target_type = state` isn't built into the list: compare with Take Treaty Port. Listed on an unbuilt canal: `te_*_canal_built` reads a canal under construction as built. |
| **Price.** Compare its infamy with Conquer State on the same state. | A quarter of it for a whole state (Zealand, Malaya), a third for Britain's Singapore, all of it for Britain's Gibraltar. The breakdown shows a "Share of the State taken" line. | The share line missing or 1 everywhere: the scope switch inside the `multiply` block isn't read; inline the province counts. |
| **Opening a play.** Start a play with Seize Strait as its goal. | The play opens; the AI target can back down or fight like any other play. | The play type isn't offered: compare `dp_te_seize_strait` with `dp_take_treaty_port`. |
| **Transfer.** Win the war (or have the target capitulate). | Only the shore provinces change hands; the rest of the state stays with its owner. On the Panama, Suez or Kiel canal both canal provinces move. The holder becomes a controller of the strait (the strait's tooltip on the map). | Nothing moves: the BROKEN line above. The whole state moves: the target state was only the shore (expected), or the engine merged it. |
| **People and buildings.** Read the self-check line, then the two states. | How many people moved, and which buildings went with the shore. Record it here; nothing in the base game documents the split. A built canal's building stays in the state that keeps it. | A shore that takes no people at all, or all of them, is worth a note for the price. |
| **Conflicts.** Add Seize Strait and Conquer State on the same state. | The game refuses the second. | Both allowed: the conflict settings don't reach a custom goal. |
| **AI.** In an observer run, grep `TE_SELF_CHECK OK te_seize_strait` for `ai=1`. | Whether the AI ever uses it. It has no weight of its own. | Never by 2000 is acceptable; record it. |

## Readings

**2026-11-09: the first enforcement read OK.** A 1.15 game, August 1872 (launch of 17:34, `debug.log`):

```
TE_SELF_CHECK OK te_seize_strait holder=Singapore ai=0 shores=0->1 holder_pop=0->59588 target_pop=596306->536274 date=August 25, 1872
```

- **Self-check and Transfer.** One shore province changed hands (`shores=0->1`) and the rest of the state stayed with its owner, who kept 536,274 people in the region: `set_owner_of_provinces` takes effect inside the effect block, so the after-reading needs no delay.
- **People.** 59,588 of the region's 596,306 went with the one province, 10.0%; the two sides sum to 444 fewer than before (0.07%). The holder had nobody in the region before, so the engine does split a state's pops when provinces leave it. Which strait and state region this was the line doesn't say, so the share can't yet be set against the region's province count; the next reading should note the state from the map or a save, and the buildings.
- **AI.** `ai=0` is right: the owner was playing Singapore (owner, 2026-11-09), so `is_ai` reads correctly in the line. The AI row is still open.
