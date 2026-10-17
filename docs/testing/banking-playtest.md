# Banking play-test checklist

What the next play-test should look at in the banking cycle. In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here.
Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Logs.** Read `debug.log`, not `error.log`, for the self-check lines; `error.log` carries the script errors.
- **Saves.** `scripts/analysis/save_country_probe.py <save> --tag <TAG> --var '^(banking_crisis_wave_|crash_severity|contagion_crash|finance_cycle_)'`
  reads a country's banking state without the game.

## Self-checks (every game)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … contagion_roll_scope` | OK once a game, when the first country a contagion cascade reached (a contagion crash spreading on, not an origin crash) has its own roll crash; BROKEN each time a contagion event's options and its roll disagree | the event's own `save_scope_as = contagion_crashed` replaced the upstream country's inherited one, so a cascade target's crash plays as a crash | `roll=crash read=scare`: the save did not replace the inherited scope, so in a cascade only the first tier can crash. `roll=scare read=crash`: the 2026-10-16 bug is back. A second contagion event open for the same country at once can overwrite `contagion_crash`, so check the line against that country's events before acting | `roll=crash read=scare`: keep the roll in a saved scope *value* set on both outcomes (`save_scope_value_as = { name = contagion_roll value = yes/no }` in `immediate`, read as `scope:contagion_roll = yes`), which overwrites whatever came in |
| `TE_SELF_CHECK … banking_entry_everywhere` | Once a game, 30 days after the first yearly pulse (an old save's first after this change) | every country that should hold `je_banking_cycle` (under the rule, not decentralized, not a rebel) does, and the yearly safety net added none: the engine activated every record | `missing=` countries still without it, `added_by_net=` how many the net has added. The engine left records out (or, for `missing`, a country formed in the last two weeks); the net carries them, a year late at most | Add the entry from a monthly pulse instead of the yearly one (`te_banking_entry_net` in `te_banking_entry_on_actions.txt`), so a country waits a month at most |

## A contagion scare plays as a scare (2026-10-16)

The European Union (cooperative economy, bubble pressure 0) got the contagion event and its cycle fell from 59.9 to 30.
Its save shows the roll was a scare (`banking_crisis_wave_scared`), yet the crash branch ran, at the tier of a
`crash_severity` of 25 left by an earlier crash, and the cascade ran from it (`banking_crisis_wave_counted`). The event's
saved scope `contagion_crashed`, which marks a crash, had come in from the upstream country, and `clear_saved_scope`
did not remove it. Every read now asks that the saved country be the event's own (`banking_contagion_own_roll_crashed`).

1. **A scare is a scare.** Under a cooperative economy, a scare takes 2 cycle value and 0.5 momentum; under a command
   economy 1 and 0.5; otherwise 3 and 1. It offers only "Close the gates" and "Maintain open markets", and the history chart gets no
   red crash marker that month.
2. **A crash is still a crash, and spreads.** A country whose own roll crashed sees the crash-only options (capital controls,
   monetary intervention, confidence messaging where its laws and institutions allow), takes a crash tier, and its
   neighbours get contagion events a week later.
3. **No `crash_severity` errors.** `error.log` has no `Failed to fetch variable for 'crash_severity'` from
   `banking_cycle_effects.txt` (the crash tiers, or the spread's severity weights) during a wave.
4. **The Great Depression waits for real crashes.** The wave count rises only with countries that crashed: a wave
   should rarely reach the event's ten countries now, where before every country a cascade touched counted.

## An event that resolves just after a revolution (2026-10-16)

`banking_cycle_post_event_refresh`, the end of nearly every banking event, now skips the phase modifiers and bars when
the country holds no `je_banking_cycle`. Bunyoro's contagion event resolved two seconds after its revolution ended,
before the winner had taken the entry over, and every `je:` read failed.

5. **No `je` errors after a revolution.** In a game with revolutions during a banking wave, `error.log` has no
   `Failed to scope to journal entry by tag 'je_banking_cycle'` from `banking_cycle_effects.txt`, and the winner's
   banking bars are right by the next month.

## Every country holds the banking entry (2026-10-17)

The entry is every country's from the first weeks of a game, dormant until its financial cycle starts: Stock Exchange and
an Urban Center of level 5, the test that used to activate the entry
(`docs/superpowers/specs/2026-10-17-banking-always-on-design.md`).

6. **A new game.** Within two weeks every country's journal holds the entry, and the Banking tab opens for all of them.
   A country without Stock Exchange or a level 5 Urban Center shows the Not Started cell (its hover the two conditions,
   ticked or crossed), its Monetary Policy readings with every control greyed under the read-only note, and Available
   Interventions with every Enable greyed under its note. No bars, no Active Policies, no history, no phase in the top
   bar.
7. **The start.** The month a country meets both conditions, its cycle appears at Stable with no momentum and no bubble,
   the controls and tools open, and a human player gets the Banking Cycle Begins notice. A country that meets the test
   in 1836 starts when its entry activates, with no notice.
8. **An old save.** Countries that already ran the cycle carry on unchanged. The rest get a dormant entry within two
   weeks, and the self-check line reads OK.
9. **A dormant central bank.** A country with a National Bank but no running cycle keeps the Dual Mandate (or its act's
   mandate under Central Bank Independence), and its dial can't be moved until the cycle starts.
10. **Rebels.** During a revolution the rebels hold no banking entry. When they win, the nation's cycle carries on where
    the loser left it.
11. **No new errors.** `error.log` has no `Failed to fetch variable` for `finance_cycle_value`, `finance_cycle_momentum`
    or `bubble_pressure` while a dormant entry's panels are open, or from the AI's banking buttons.
