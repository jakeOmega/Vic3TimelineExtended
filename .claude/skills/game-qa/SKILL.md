---
description: Launch Victoria 3 from a session and check something in the running game - fire an event as a country and pick each option, read triggers and script values, advance time, take a screenshot - with the owner's saves and settings snapshotted first and put back afterwards. Use whenever the user asks to test, verify or check something in game, to "try event X as Y", to confirm an effect, trigger or modifier in the running game, to make a fresh save, or mentions the QA harness, `game_qa`, a session, a held snapshot or a left overlay. Not for reading logs after the owner's own play (see log-triage).
---

# Game QA skill

`python3 -m game_qa` starts the game, drives it and restores the owner's files. Every verb prints one JSON object and exits 0, or 2 for a refusal, a hold or an error. A refusal says what to run next in `next`: do that, not something of your own.

## Three rules before anything else

1. **Ask the owner before launching**, unless they granted launches for this session in their own words. A grant has limits (a time, "after I leave"): keep to them. Even with a grant the tool's gate decides: it refuses beside a game it did not start, and on a busy GPU. Never pass `--owner-confirmed-busy` unless the owner was asked about that reading and said yes.
2. **The game starts only through `start`** (or part 1's `launch`). Never run `victoria3.exe`, the launcher or PowerShell yourself, never end a game process by hand, and never edit, copy or delete anything in the game's user-data folder: the verbs do all of it, with checks.
3. **A hold is the owner's.** `held` in a reply means the tool could not prove that putting the files back was safe (the owner may have played since), so it stopped. Most holds change nothing but the run's playset, which goes back when no game is running. Two come later: `modified_during_restore` (a file changed under the restore; the files before it were already put back) and `retime_unverified` (everything was put back, and one file was left with the snapshot's time over bytes nobody could vouch for). The reply's `restored`, `removed` and `retimed` list what was done. Only the owner resolves a hold. Tell them which snapshot and why, and start nothing more.

## The order of verbs

```bash
python3 -m game_qa doctor                       # ready? starts nothing
python3 -m game_qa start --permission "<the owner's words, and when>" --as FRA \
        [--setup NAME=FILE]... [--playset mod_only|current] [--save NAME]
python3 -m game_qa read "c:FRA.gdp" "root.has_technology_researched = railways"
python3 -m game_qa run-setup NAME               # a setup given at start, run through its event
python3 -m game_qa console "event my_events.3"
python3 -m game_qa events                       # what is pending, with numeric ids
python3 -m game_qa pick 0 my_events.3           # option index is 0-based
python3 -m game_qa try-event my_events.3 --setup NAME --read "c:FRA.gdp" --read "..."
python3 -m game_qa enter-game ; python3 -m game_qa advance 10 ; python3 -m game_qa shot
python3 -m game_qa selfchecks [--run ID]        # the mod's TE_SELF_CHECK verdicts, every BROKEN first
python3 -m game_qa stop                         # always, even after a failure
```

- **`start`** takes two to four minutes: it snapshots, builds the overlay mod, makes a fresh save if none is cached for this build (an unattended run of its own), loads it, attaches the debugger and opens the console. `--permission` records where the go-ahead came from. Without `--save` the game sits on the fresh save's country-select screen with time stopped, which is all that reads, events and picks need. `--playset mod_only` (the default) loads only this mod's deployed folder; `current` loads the owner's playset. The build under test is whatever is in the deployed mod folder, so deploy first if the change is not there.
- **A setup** is a file holding an effect block's body, run in the played country's scope. Give it at `start`; it cannot be added later.
- **`read`** evaluates triggers and values at a breakpoint in the played country's scope: `c:TAG.<value>`, `root.<value>`, a script value's name, `c:TAG.var:x`, a trigger. Write a trigger bare (`has_modifier = x`); `c:FRA.has_modifier = x` is refused by the game as an unknown trigger type. An unset variable reads 0, so read `has_variable = x` when that matters. A read that fails comes back `ok: false` with the game's words; the verb still exits 0.
- **`console`** types one command (ASCII, at most 64 characters). `event <id>` ignores the event's trigger and cooldown. There is no console `effect` or `run`: use a setup.
- **`try-event`** is the owner's first check: for each option it runs the setup, fires the event, reads, picks, reads again, and writes a table to the run folder. The options share one game, each starting from the state the one before left, so write the setup to put back what the options change, or say so when reporting. It exits 0 only when every option fired and was picked.
- **`enter-game`** makes the two clicks past the country-select screen (about a minute); **`advance N`** lets at least N days pass and pauses again. Only needed when the check needs time to pass. A variable a setup set on the country-select screen survives entering (verified 2026-11-11; laws and modifiers changed there were not read afterwards). **A setup that changes a law there stops `enter-game`**: the game's "We now have …" window covers the click, the reply is `not_entered` with "the date stayed", and no verb closes that window yet (#1598). So enter first, then run setups that change laws. That reply locks nothing, since nothing moved: `enter-game` can be run again (`advance` runs it again), and works once nothing covers the click. Any other failure after the clicks (`not_entered` with a `cause`, `left_running`, a code such as `tag_failed`; `status` then shows `left_running: true`) means the game may be in play: `advance` and `enter-game` are refused until `stop`, while `console`, `events` and `pick` still work.
- **`selfchecks [--run ID]`** prints the verdicts of the mod's `TE_SELF_CHECK` lines for a run, the newest by default: `broken` names each BROKEN check once, and `checks` has a row per check and source (`name`, `verdict`, `line`, `source`), each BROKEN first, then a START whose verdict never came. `source: fixture` marks the lines of the run that made the fresh save, the only place the checks a new game logs at its setup ever appear; they are kept, with the `TE_MONUMENTS` lines, in `<backup root>/fixtures/<key>/lines.log` for as long as that save is. With a session live it flushes the game's log first (one empty read; `flushed` says whether it could, `not_flushed` why not). It needs no session, works after `stop`, and exits 0 whatever the verdicts, so read `broken`. `stop` writes the same list into `summary.md`. A line is shown as the run's only where that is proved, and the reply says what that cost: `fixture.kept: false` with a `detail` (the fresh save predates this, its run did not get as far as keeping its lines, keeping them failed, or it was made again after the run asked about); `log_not_read` (or a note at `stop`) when the game had ended by itself, or could not be proved alive after its log was read, so that the lines could not be trusted to be its own; and `session.unvouched`, with `unvouched: true` on each session row, when `watch` saw another Victoria 3 process beside the run's game, which no proof rules out. Report those with the verdicts: a missing line is not an OK, and an unvouched row is not a verdict.
- **Before calling a read BROKEN**: pair every expected "no" with a read of the same form that must say "yes"; a read with `ok: false` is a form the harness cannot evaluate, not a "no" (the forms that work are in `docs/guides/python_tools.md`, "What the first play-test runs added"); and the save is 2 January 1836, so what a system seeds at the first monthly pulse is not there until February.
- **`stop`** ends the harness's own game, waits for its watcher, restores, removes the overlay and ends the server. Read its reply.

## Reading a stop

| Reply | Meaning | Do |
|---|---|---|
| `outcome: restored` | The owner's files are back as they were | Done. Run `doctor` to confirm nothing is left |
| `outcome: held` | The restore stopped for the owner to decide; `restored`, `removed` and `retimed` list what it had put back by then (for most holds, the playset at most) | Report the snapshot id and the reason; start nothing. After `retime_unverified`, name the file too (the journal's last `held` entry, `files`) and what to do about it (`docs/guides/python_tools.md`, the hardenings bullet) |
| `outcome: game_left_up` | The game may still be running; nothing was restored beside it | Follow `next` exactly; ask the owner to close the game if it says so |
| `outcome: refused` | The restore would not run yet | `stop` again when `next` says so; otherwise `recover`, then `remove-overlay` |
| `overlay_kept: true` | The overlay folder was left because a playset may still name it | `remove-overlay`, once `next` allows it. Never delete the folder by hand |

## After a refusal or a crash

- `no_answer`: the verb in front may still be running. `status`, wait, never start a second session.
- `watch_ended`: the game has gone or could not be proved to be the harness's own. Nothing more is typed. `stop`.
- `session_running`, `overlay_left`, `playset_not_restored`, an unfinished run in `doctor`: an earlier session did not finish. `stop` if its server answers; otherwise, once no Victoria 3 process runs, `recover`, then `remove-overlay`, then `doctor`.
- The session's server died: the game's watcher keeps recording by itself. Same path: no game running, `recover`, `remove-overlay`. If the game is still up, no verb ends it: ask the owner to close it, and run nothing until they have. This path has only been tested against fakes, so read each reply before the next step.
- Anything the verbs cannot finish: stop, leave the files alone, and tell the owner what `doctor` and `held` print.

## What to tell the owner afterwards

What was checked and what the game answered (attach the run folder's `summary.md`, under `<backup root>/runs/<snapshot id>/`; its Self-checks table lists every `TE_SELF_CHECK` verdict, BROKEN first), whether the stop restored or held, whether the game is closed, and anything the run changed that the restore does not cover (it covers saves, autosaves, the Continue pointer, the playset, console history, settings and logs; the harness's fresh save `te_qa_fixture_<key>.v3` stays in `save games/` on purpose). Detail and the engine facts behind the verbs: `docs/guides/python_tools.md` § "Driving the game from a session" and `docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md`.
