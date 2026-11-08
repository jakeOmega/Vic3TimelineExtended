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
  line with `holder_pop=before->after target_pop=before->after` for the strait's state region and `ai=0|1`.

## Self-checks

| Line | OK means | If BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK\|BROKEN te_seize_strait` | The holder owns land in the strait's state region after the transfer. | `set_owner_of_provinces` didn't run or found no province: check `debug.log` for a script error on `te_seize_strait_shores`, and whether the state still held the shore when the peace was signed. |

## First release (2026-11-07)

| Check | Expect | If it fails |
|---|---|---|
| **Offered.** In a play against a country holding a shore state, open the war goal list. | Seize Strait is listed for that state, not for its other states, and not for a canal zone whose canal isn't built. | Not listed at all: the custom kind with `target_type = state` isn't built into the list; try `skip_build_list` off/on and compare with Take Treaty Port. Listed on an unbuilt canal: `te_*_canal_built` reads a canal under construction as built. |
| **Price.** Compare its infamy with Conquer State on the same state. | A quarter of it for a whole state (Zealand, Malaya), a third for Britain's Singapore, all of it for Britain's Gibraltar. The breakdown shows a "Share of the State taken" line. | The share line missing or 1 everywhere: the scope switch inside the `multiply` block isn't read; inline the province counts. |
| **Opening a play.** Start a play with Seize Strait as its goal. | The play opens; the AI target can back down or fight like any other play. | The play type isn't offered: compare `dp_te_seize_strait` with `dp_take_treaty_port`. |
| **Transfer.** Win the war (or have the target capitulate). | Only the shore provinces change hands; the rest of the state stays with its owner. On the Panama, Suez or Kiel canal both canal provinces move. The holder becomes a controller of the strait (the strait's tooltip on the map). | Nothing moves: the BROKEN line above. The whole state moves: the target state was only the shore (expected), or the engine merged it. |
| **People and buildings.** Read the self-check line, then the two states. | How many people moved, and which buildings went with the shore. Record it here; nothing in the base game documents the split. A built canal's building stays in the state that keeps it. | A shore that takes no people at all, or all of them, is worth a note for the price. |
| **Conflicts.** Add Seize Strait and Conquer State on the same state. | The game refuses the second. | Both allowed: the conflict settings don't reach a custom goal. |
| **AI.** In an observer run, grep `TE_SELF_CHECK OK te_seize_strait` for `ai=1`. | Whether the AI ever uses it. It has no weight of its own. | Never by 2000 is acceptable; record it. |
