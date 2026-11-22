# In-game QA harness results: 2026-11-19, `script-docs` (#1907)

The first live runs of `python3 -m game_qa script-docs`, the verb that takes the mods-off engine-doc dump of a vanilla
bump. Three runs from the branch of the PR that closes #1907, each a little further on than the one before: the first
two crashed the game and showed why, and the third took the dump.

**Game:** Victoria 3 1.15.2 (Ivan-Chai), installed that morning. **Playset:** `launch --playset none`; the owner's
`content_load.json` already enabled no mod (their own mods-off dump that morning), so nothing was written to it.
**Launches:** three, on the owner's grant in their request for #1907 ("Any session running the runbook has
permission, from being asked to run the runbook, to launch the game as long as the GPU has low usage (below 50%,
say) and the game is not already running"); the second after they closed the first run's crash reporter and said to
go ahead. Before each, `doctor` was clean, `gate` answered ok and the GPU load was 14 to 26%.

**Run folders** (under the backup root): `runs/20261119T181735Z/`, `…182456Z/`, `…183041Z/`.

## Run 1: the session's console probe crashes the bare main menu (`runs/20261119T181735Z/`)

Arguments `-gdpr-compliant -debug_mode`, no save: the game came up at its main menu 70 s after the launch. The console
was opened as a session opens it, with the probe `select_event_option list`: the history took it, so the console
counted as open, and in the same second the game crashed. Its `debug.log`, copied into
`crashes/victoria3_01261019_111859/`:

```
[11:18:59][console.cpp:1175]: Running console command: select_event_option list
[11:18:59][pdx_assert.cpp:641]: Assertion failed: NGameState::GameStateAccess._Value != EGameStateAccess::Uninitialized
```

then `EXCEPTION_ACCESS_VIOLATION` (`exception.txt`). The next step found the window gone (`game_gone`) and the stop
found the game already exited. **The restore was refused**: `Permission denied` replacing `logs/code_revisions.log`.
The game's crash reporter ("Paradox Crash Reporter", `CrashReporter.exe`) was up on the owner's desktop and held
`logs/` open. The console history had gone back by then; the logs had not. Nothing was ended by hand: the owner closed
the reporter, and `recover` then finished the snapshot (`held: false`, 44 logs restored, the rest retimed).

## Run 2: `script_docs` itself crashes the bare main menu (`runs/20261119T182456Z/`)

Fixed for this run: the console probed with `log list` (the log system's own command, which needs no game state),
and `-no_crash_reporter` added (the 1.15.2 binary: "Never launch the crash reporter app on a crash, so an unattended
run leaves no modal window behind"). The probe went through. `script_docs` crashed the game with the same assertion,
in the second it ran, after writing `effects.log` and opening three more logs empty. No reporter came up, and the
stop's restore went through (`outcome: restored`), so the flag did what it says.

That meant the owner's own dump that morning had not been taken at the bare main menu. Their `debug.log` shows
vanilla's new-game setup (`common/on_actions/00_code_on_actions.txt:4298: Tory Party Created - Great Britain`, and
the other parties) at 10:27:23 and a map camera at 10:27:32, then `script_docs` at 10:27:47: they had opened a new
game's country-select screen, which has a game state.

## Run 3: a hands-off new game, then the dump (`runs/20261119T183041Z/`)

Arguments `-gdpr-compliant -debug_mode -no_crash_reporter -handsoff -run_until=1836.3.31`: the game starts a new game
by itself and would end before the first quarterly autosave. The session waits for a line of script in `debug.log`
(`][jomini_effect_impl.cpp:`) before the command.

| Step | Time (UTC) |
|---|---|
| `held`, `snapshot` | 18:30:40, 18:30:42 |
| `launch` (pid recorded), window | 18:30:52, 18:30:54 |
| vanilla's first party line (the game state) | 18:31:48 |
| console's first answer (`log list`) | 18:32:07 |
| `script_docs` typed; all six logs rewritten and settled 3 s; copied and checked | 18:32:14 |
| `kill` (the game was alive), restore | 18:32:14, 18:32:41 |

The restore put back 50 files and removed the run's `logs/gametimer_20261119_113149.tsv`; nothing was held. The dump
went to a scratch folder, since `~/src/vic3-engine-docs/1.15.2/docs` holds the owner's hand-taken dump.

**Against the owner's hand-taken 1.15.2 dump** (#1907's "done when"): `vanilla_patch_diff.py docs <hand> <run 3>
--show-changed` reported 0 removed, 0 added, 0 changed in effects, triggers, event targets, modifiers and on-actions.
`modifiers.log`, `event_targets.log`, `on_actions.log` and `custom_localization.log` were byte-identical. In
`effects.log` (3,667 sections) and `triggers.log` (2,048) both dumps had the same section names, and every section that
differed (2,584 and 958) was a regional iterator (`every_/any_/random_/ordered_…_in_…`), whose description the dump
reshuffles each time. The mod's marker `country_add_anticolonial_ideology_to_igs_bool` was absent.

## What these settle

- `select_event_option list` and `script_docs` both need a game state: at the bare main menu each crashes the game.
  `log list` does not. A session never meets this, since it always loads a save first.
- A crash with the crash reporter up holds `logs/` open, and the restore cannot finish until the reporter is closed.
  `-no_crash_reporter` keeps it away.
- `-handsoff -run_until=<a short run's end>` with no mod and no scripted test starts a new game whose console takes
  `script_docs` once vanilla's setup has run. The command, the six logs and their settling took 5 s; the run's end
  date was not reached.

## Not run live

The refusals other than the two crashes' (`stale_docs`, `mod_loaded`, `out_exists`, `out_not_a_dump`,
`version_mismatch`, `no_game_state`, `crashed`, a copy that fails) are tested against the fakes only; `crashed` and
`out_not_a_dump` came from the independent review of the PR, after these runs. So is the copy to the default folder
`~/src/vic3-engine-docs/<version>/docs`: the live run wrote to a scratch folder with `--out`. And so is `--playset
none`'s write: the owner's playset already enabled nothing, so the runs left `content_load.json` alone.
