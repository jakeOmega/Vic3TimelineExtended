# Homelands play-test checklist

In-game checks for the dynamic homelands and the base-game content that reads them
(`docs/systems/mod_systems/pops_and_migration.md`). Read the self-check lines from `debug.log` after any game long
enough for a homeland to go.

## Self-checks (every game)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … renaissance_homeless_outcome` | Once a game, on the global monthly pulse, while the Ukrainian or Byelorussian Cultural Renaissance is open and its culture has no homeland left. TEMPORARY: delete `common/on_actions/te_renaissance_selfcheck_on_actions.txt` once a verdict is read | The entry concluded through the hidden invalid outcome `te_vanilla_cultural_renaissances.txt` injects (`te_renaissance_homeless_fired` is set) | The entry stayed active through two monthly checks with no state a homeland of its culture: the engine does not conclude a vanilla entry through an INJECTed invalid outcome | REPLACE the two entries (`je_ukraine_cultural_renaissance`, `je_belarus_cultural_renaissance`), copied from vanilla, with `te_homeland_none_left` in `is_shown_when_inactive` and as an invalid outcome of their own |

No line: neither culture lost its last homeland while its entry was open, which is most games.

## The Cultural Renaissances close without a homeland (2026-11-08)

A Workshop player saw the Byelorussian Renaissance open and progress after the dynamic homelands had removed every
Byelorussian homeland. To force it: as Russia, raise the removal threshold (Violent Hostility, or a law that raises
it) and let the Byelorussian homelands go, or remove them from the console, then raise Byelorussian fervor past 20.

1. **The entry closes.** Within a month of opening, the Byelorussian Renaissance leaves the journal; a concluded copy
   reads "ended with no homeland of its culture left". No national awakening or Belarus independence event follows.
2. **An open entry closes too.** With the entry already open, remove the last Byelorussian homeland: it closes within
   a month.
3. **With a homeland it runs.** A Byelorussian homeland left anywhere keeps the entry open and running as in the
   base game.
