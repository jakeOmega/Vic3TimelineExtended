# Banking play-test checklist

What the next play-test should look at in the banking cycle. In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here.
Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Logs.** Read `debug.log`, not `error.log`, for the self-check lines; `error.log` carries the script errors.
- **Saves.** `scripts/analysis/save_country_probe.py <save> --tag <TAG> --var '^(banking_crisis_wave_|banking_contagion_|crash_severity|contagion_crash|finance_cycle_)'`
  reads a country's banking state without the game. The contagion event's options leave modifiers whose start
  dates give the cascade tier: a pulse's contagion events land on the 7th (reached by the crash that started the
  wave), the 14th (by a first-tier crash), the 21st and the 28th.

## Self-checks (every game)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … contagion_roll_scope` | Judged only for a contagion event that was alone: no other copy open for the same country between its roll and its answer (`open=1`). OK once a game, when the first country a contagion cascade reached (a contagion crash spreading on, not an origin crash) has its own roll crash; BROKEN each time a lone event's options and its roll disagree; NO_VERDICT each time they disagree while another copy is open (`open=2` or more) | the event's own `save_scope_as = contagion_crashed` replaced the upstream country's inherited one, so a cascade target's crash plays as a crash. The 2026-10-17 autosave already shows this: targets two and three tiers out had taken the crash-only options | `roll=crash read=scare open=1`: the save did not replace the inherited scope, so in a cascade only the first tier can crash. `roll=scare read=crash open=1`: a scare took the crash options, the 2026-10-16 bug. NO_VERDICT is no fault: two copies share `contagion_crash`, the later roll overwrote the earlier one's, and each copy's options followed its own (the five BROKEN lines of 2026-10-17 were this). A country whose copy never resolved (annexed first) is not judged again | A BROKEN with `open=1`: drop the saved scope. Mark a country as having a contagion event pending when the spread reaches it (skipped by the spread like `banking_crisis_wave_hit`, cleared in `after`), so only one copy is ever open, and read the roll from `var:contagion_crash` in the text, options and cascade. That changes play (a country two origins reach in one pulse gets one event, not two), so it is the owner's call. The old fallback, a saved scope *value* set on both outcomes, is withdrawn: it needs the same replacement, and where that fails a scare inherits the upstream country's crash, the 2026-10-16 bug |

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

## Two contagion events open at once (2026-10-17)

The observer run of 2026-10-17 (1836 to 1898) logged five `contagion_roll_scope` BROKEN lines, four
`roll=scare read=crash` and one `roll=crash read=scare`. None was the engine. Every country's banking pulse runs on
the same day, and a second origin crashing in that pulse re-runs `banking_crisis_wave_init`, which clears every
reached mark, so a country can be reached twice: Austria took a scare on 1898.8.7 and, reached again by a
first-tier crash, a crash on 8.14. When both origins reach it in the pulse itself, two copies of the event are open
at once. They share `contagion_crash`, the later roll overwrites the earlier one's, and the earlier copy's check
compared its own roll with the other copy's. The options had followed each copy's own roll. The check now counts
the copies open (`banking_contagion_open`) and judges only a copy that was alone; the title, description and
flavour read the event's own roll, as the options do.

6. **No `contagion_roll_scope` BROKEN.** Expect NO_VERDICT lines about as often as the BROKEN ones came (five in
   sixty years), each with `open=2` or more, and the OK once. A BROKEN with `open=1` is real: take the fallback in
   the table.
7. **The text matches the options.** A country whose own roll crashed reads "Cascading Financial Collapse" and the
   cascade description and sees the crash-only options where its laws and institutions allow; a scare reads
   "Contagion from Abroad" (or "Financial Contagion" after a severe crash) and gets only "Close the gates" and
   "Maintain open markets". When two contagion events reach the player at once, each one's text matches its own
   options.
