# In-game QA harness: a Claude session drives Victoria 3 (2026-11-10)

> **Status: design, nothing built.** Written against `main` at `d37b8be` and the game at
> 1.15.0 (Ivan-Chai, build `6338547985`). Every engine fact below is tagged **verified**
> (seen in a probe launch on the owner's machine on 2026-11-10) or **assumed** (§ 7 lists
> the assumptions, each with a fallback; settling them is the plan's first task).

## 1. The request

The owner, 2026-11-10:

- "I am interested in creating a harness or other tool to allow sessions of Claude on
  machines with a game install to launch the game and perform actions to automate QA
  testing. I think a decent first functionality would be just being able to run commands
  in the console (needs the game launched with -debug_mode) and click event options.
  This, combined with reading the log, opens up a lot for automated QA."
- The first real check, confirmed from a suggestion: "fire event X as country Y, pick each
  option, confirm the effects", and "It'd also allow confirming effects work as expected,
  as well as reads, triggers, etc."

## 2. Decided by the owner (2026-11-10)

- **Permission to launch.** "It should ask for permission unless I have granted session
  level permission to launch the game. I will typically grant this permission when I am
  not on my computer ... so I would grant it to the whole session."
- **GPU check.** "A good check may be to check if the GPU is under heavy usage, and if so,
  double check with me. If not, it is almost certainly fine (worst case is I am about to
  launch the game or similar and lose a few minutes)."
- **Backups.** "Maybe we should auto-backup the auto saves and any saves that will be used
  in the future?" The owner then agreed ("Sounds good!") to the proposal in § 5.3,
  including its two defaults: keep the last five backups, and store them on `D:`.

Everything else in this document is the designer's call (§ 9 lists the ones worth
checking) or is left to the builder (§ 10).

## 3. What the game offers (probed 2026-11-10)

Eight launches on the owner's machine. The game was started from WSL straight from
`binaries/victoria3.exe`, with Steam running and no launcher; the DLC stays enabled that
way (**verified**, `session.getenableddlcs`).

### 3.1 Launch arguments

| Argument | What it does | Status |
|---|---|---|
| `-debug_mode` | Console and debug tools | verified |
| `-loadsave=<name>` | Loads `save games/<name>.v3` with no menu clicks. About 2 minutes to a usable console with the mod. A name with no spaces was used each time | verified |
| `-handsoff` | Starts a new game unattended, in observer mode, running and AI-played | verified |
| `-run_until=1836.2.10` | With `-handsoff`: the game quits by itself on that date. 40 days took under 2 minutes from launch | verified |
| `-start_tag=GBR` | With `-handsoff`: observes that country. Alone: stops at the main menu | verified |
| `-scripted_tests` | Evaluates the engine's scripted tests, including files in a mod folder's `tools/scripted_tests/`. A failing test writes `save games/TEST_FAIL_<test>_<date>.v3` | verified (the save); result reporting **not** verified: `tests.txt` held only a `Tests:` header |
| `-script_debugger` | Opens a debug-adapter socket on `127.0.0.1:6111`. Not open without it | verified |
| `-develop` | Not needed. Did not unlock the console's `save` | verified |

### 3.2 Console commands

`help` with no argument writes the full list to `debug.log`. The ones that matter here:

| Command | Behavior | Status |
|---|---|---|
| `event <id> [TAG]` | Fires the event for the played country. Its `immediate` runs at once, paused or not | verified |
| `select_event_option list` | Prints one line per pending event of the played country: `<numeric id> <event id> options=<n>` | verified |
| `select_event_option <index> [<numeric id>]` | Picks an option "as if clicked". The index is 0-based. The id is the number, not the event's name. With one event pending and no id, it picked that one. The option's effects ran in the same second, paused | verified, in a game entered by `-loadsave` |
| `tag <TAG>` | "Now Playing - France". Worked on the loaded save's country-select screen and again mid-session to change country | verified |
| `load`, `save` | Refused: "Command available only for developers" | verified |
| `run <file>`, `effect` | Do not exist | verified (`help run` lists only `debug_supply_runs`) |

**Under `-handsoff` option selection is not usable** (verified): the console printed
"Selected option", nothing ran until the next tick, and then other options ran than the
ones chosen, because the AI plays every country. Event checks need a game entered with
`-loadsave`.

### 3.3 Running script without a `run` command

A hidden event whose `immediate` calls a scripted effect is the way to run arbitrary
effects: `event <carrier id>` (**verified**; the repo's `te_debug_*` events already use
this by hand). Editing the effect's file while the game runs hot-reloads it
(**verified**), but with this mod a reload takes about 40 seconds, console commands typed
during it are dropped ("You can't add new commands while the console is still running
commands"), and the reload writes thousands of `Adding effect after PostInitAndValidate`
lines, which rotated all six `debug.log` generations within one second. A scripted-effect
file added mid-game did not run on its first call, only after the next reload; an event
file added mid-game was usable at once.

### 3.4 Keystrokes and the window

- **Verified:** `SendInput` with scancodes from a Windows-side process reaches the game.
  Scancode `0x29` opens the console, at the main menu, on the country-select screen and
  in-game; space toggles pause; text sent as Unicode key events lands in the console.
- **Verified:** the console key was ignored twice while the game was busy (once during a
  hot reload). A command's arrival has to be confirmed, not assumed.
- **Verified:** `console_history.txt` in the user-data folder gains each command as it is
  entered.
- **Verified:** the game runs full-screen at 3840x2160 on the primary monitor of a
  three-monitor desktop. A window screenshot through GDI works, including over the
  owner's Chrome Remote Desktop session. An unlocked desktop is required.
- **Verified:** the game can bring the owner's Notepad to the front showing `error.log`
  (seen during one load and at an unattended run's exit). Keys must never be sent unless
  the game's window is the foreground window.

### 3.5 Reading results

- **`debug.log` is block-buffered** (verified): lines are written in blocks of about
  4 KB, and a line was seen to sit unwritten for over a minute. Any 4 KB of further log
  output pushes it out; the probes used the console's `help ndefines.ngui` (about 500
  lines).
- **Console input and output are logged** to `debug.log` as `console.cpp` lines:
  `Running console command: …`, `console_success: …`, `console_failure: …` (verified).
- **`debug_log` effects** print with their file and line, and data functions in the text
  resolve: `[THIS.GetCountry.GetTagName]`, `[TimeKeeper.GetCurrentDate.GetString]`
  (verified).
- **The debugger** speaks the Debug Adapter Protocol (verified: `initialize`, `launch`,
  `setBreakpoints`, `configurationDone`, `stackTrace`, `scopes`, `variables`, `evaluate`,
  `continue`). A breakpoint on a line of a mod file is accepted by its Windows path and
  stops the game when that line runs. Stopped there:
  - `scopes` and `variables` give `this`, `root`, `prev` and the saved scopes;
  - `evaluate` answers a trigger (`is_player = yes` returned `yes` and the trigger's
    explanation; `any_scope_state = { is_capital = yes }` worked) and a dotted value
    (`c:FRA.gdp` returned `21570770.55692`);
  - a bare name (`gdp`, `root`, `var:x`) is refused as "not a valid trigger or script
    value";
  - `evaluate` is refused unless the game is stopped at a breakpoint;
  - each trigger evaluation made the engine re-run a validator that wrote about 900
    "is set but is never used" lines to `error.log`.
- **The debugger streams `error.log` lines** as `output` events (3,779 seen, all
  `category: stderr`). No `debug_log` or console line came through it.
- `victoria3_win_console.exe` is a stub that relays checksum lines; its standard input
  does nothing (verified).

### 3.6 A fresh save without clicks

A scripted test in the mod folder with `fail = { game_date > "1836.1.1" }`, run as
`-debug_mode -handsoff -scripted_tests -run_until=1836.1.4`, left
`TEST_FAIL_<test>_2 January, 1836.v3` (133 MB, plain text) in 90 seconds: a new game on
whatever build and playset were loaded (**verified**). Renamed and loaded with
`-loadsave`, it opens on the country-select screen, where the console works and `tag`,
`event` and `select_event_option` all behaved as in § 3.2 (**verified**).

### 3.7 What went wrong during the probes

These set the anti-goals in § 4.

- An unattended run with no end date played to July 1836, wrote two quarterly autosaves
  into the owner's `save games/`, pushed their two oldest rotating autosaves off the end
  and repointed `continue_game.json`. The backup was then deleted by the same command
  that reported the change.
- Every launch rotates the owner's game logs; a morning session's logs survived only
  because they had been copied first.
- The deployed mod was behind `main`, and the playset held three Workshop mods beside
  this one. Neither was chosen; both were just what the machine had.

## 4. Goals, non-goals, anti-goals

**Goals (version 1)**

1. A Claude session on a machine with the game can, with no clicks: get a game on the
   deployed build, play as a chosen country, run a prepared effect, fire an event, list
   and pick its options, and read triggers and values before and after.
2. The owner's saves, Continue pointer, console history and logs are as they were when
   the run ends, however it ends.
3. Every step is confirmed from a primary source (the console history, the log, the
   debugger), and a run leaves a report a later session can read.
4. Nothing here needs a game to pass CI: the harness's own tests run against fakes.

**Non-goals (version 1)**

- Clicking GUI widgets (journal-entry buttons, panels). Screenshots are provided for
  looking, not for locating buttons.
- Choosing which build or branch is tested: version 1 tests the deploy folder as it
  stands and reports its drift (§ 5.9). Deploying stays the existing, separate step.
- Long unattended soak runs and the engine's scripted-test reporting (phase 3).
- A declarative check-file format kept in the repo as a regression suite (phase 2).
- Machines without a desktop session, native Linux, multiplayer.

**Anti-goals: these make it a failure even if it works**

- Losing or altering anything of the owner's in the user-data folder.
- Typing into a window that is not the game.
- Closing a game process the harness did not start.
- Launching without the owner's go-ahead (§ 5.2).
- Harness script reaching players: nothing of it lives under the repo's `common/`,
  `events/`, `gui/` or `localization/`, and `scripts/deploy.sh` never copies it.

## 5. Design

### 5.1 Parts

- **Driver** (Python, WSL side): owns a run from gate to restore, tails the logs, speaks
  the debugger protocol, writes the report. It stays up between commands as a small local
  service, the way `mod_state_server.py` does, because a session works one tool call at a
  time and the game outlives each call.
- **Windows helper**: one stdlib-only Python file run with the Windows `python.exe`
  (3.11 is installed on the owner's machine), started by the driver through WSL interop
  and spoken to over its standard input and output. It does only what must happen on the
  Windows side: start the game and report its process id, report and set the foreground
  window, send keys, take a window screenshot, end the process it started, and relay
  bytes to and from `127.0.0.1:6111` (WSL's default networking cannot reach a Windows
  loopback socket).
- **Overlay**: the harness's own script files, generated at run time from templates kept
  beside the driver (§ 5.4).
- **Command line** over the driver, one verb per step (§ 5.8), and the same calls as a
  Python API for scripts.
- **Skill** `.claude/skills/game-qa/`: the procedure a session follows, starting with
  the permission rule.

Paths come from `path_constants.py`; two new entries are needed, the game's user-data
folder (today only `game_logs_path` and `mod_deploy_target` point into it) and the
backup root.

### 5.2 The launch gate

A session asks the owner before launching unless the owner has granted launches for that
session. A grant covers the session it was given in and no later one. That rule lives in
the skill, because only the conversation knows it. The tool backs it with three checks:

1. **A stated permission.** The launch verb takes a required `--permission` text ("asked
   12:40", "session grant") and copies it into the report. It cannot check the claim; it
   makes a session say where its permission came from before a launch happens.
2. **A running game.** If a `victoria3.exe` exists that this harness did not start, the
   launch stops and the session asks the owner. The harness never ends that process.
3. **GPU load**, even with a grant: `nvidia-smi` sampled five times over five seconds. A
   mean utilization of 50% or more, or more than half the card's memory in use, stops the
   launch with a "busy" result; the session then double-checks with the owner and repeats
   the launch with `--owner-confirmed-busy`. (The owner's machine read 14% and 1.6 of
   10 GB while idle with a remote-desktop session and a video playing.)

The harness ends only the process id it started, never by image name.

### 5.3 Protecting the owner's files

Before every launch the driver takes a **snapshot** into the backup root (default
`/mnt/d/vic3_qa_backups/`, since the WSL disk shares `C:`):

- `save games/autosave*.v3`, `continue_game.json`, `console_history.txt`,
  `pdx_settings.json`, `content_load.json`;
- any save the run will load;
- every file in the game's `logs/` folder (a whole copy: `log_triage.py`'s `snapshot()`
  takes seven families and skips empty files, which is not enough to put the folder
  back).

After the game exits, by any route, the driver **compares and restores**: an owner file
that changed is put back (the autosave rotation as a set, the Continue pointer, the
console history, the playset file, the logs folder), and the files the run created are
removed (saves it named, any `TEST_FAIL_*` it caused, `tests.txt`). The run's own logs
live in its report. The report says what was restored.

Between the snapshot and the exit of the harness's own game, nothing else may have
written these files (the gate refuses to start beside another game), so that restore is a
plain compare and copy.

Rules that come straight from § 3.7:

- A snapshot is never deleted by the run that made it. Pruning to the last five happens
  at the start of a later run, and only after that run's own snapshot is complete.
- A file unchanged since the previous snapshot is not copied again, but every snapshot
  kept must stay restorable on its own after others are pruned.
- A run records "started" before launching, a heartbeat while its game is up, and
  "restored" after. A driver that starts and finds a run without "restored" (the session
  died, the machine rebooted) looks at the files first. If none was modified after that
  run's last heartbeat, it finishes the restore. If any was, the owner has played since:
  it restores nothing, marks that snapshot **held** (never pruned, named in every later
  report until the owner says what to do with it) and carries on with the new run. A held
  snapshot does not block later runs.
- Every unattended launch carries `-run_until`.
- Saves the harness makes are named `te_qa_*`.

### 5.4 The overlay

The overlay holds a carrier event, the setup effects for the run, and the scripted test
that makes the fixture (§ 5.5). It is generated into its own mod folder,
`mod/te_qa_overlay/` beside the deployed mod, with its own `.metadata/metadata.json`, and
enabled for the run by adding it to `content_load.json` (snapshotted and restored like
the rest). It is kept out of `mod_deploy_target` because `scripts/deploy.sh` and the
deploy watcher sync with `--delete` and would remove it mid-run. That a second mod folder
added this way loads on a direct launch is assumption A3.

The same control of `content_load.json` sets the playset: by default a run enables this
mod and the overlay only, so a failure is this mod's; `--playset current` keeps whatever
the owner had enabled. The report lists what was enabled either way.

- **Carrier event** `te_qa.1`: hidden, `immediate` logs a marker line and calls
  `te_qa_setup_<name>` chosen by a variable or, simpler, one carrier event per prepared
  effect. Its first line is where the debugger's breakpoint goes (§ 5.7).
- **Setup effects** are written by the session before launch: plain Paradox script in a
  scratch file, copied into the overlay by the driver, one named effect each. They put a
  country in the state a check needs (variables, modifiers, laws, saved scopes) and, for
  an event that reads scopes its caller saved, end with `trigger_event` (assumption A1).
  `trigger_event` checks the receiving event's `trigger` and `cooldown` and fails silently
  (`docs/guides/scripting_best_practices.md` § "A Flag the Sender Sets Before
  `trigger_event` Must Not Gate the Event It Fires"), so a setup that fires an event this
  way must first make its trigger true. Whether console `event` checks either is
  assumption A6.
- **Hot reload is not part of an automated run.** Everything a run needs is in the
  overlay before launch. A session exploring by hand may still edit and wait the 40
  seconds; the driver then refuses console input until the reload's log burst has ended.

### 5.5 Getting into a game

1. **Fixture.** The key is the game version, the playset, and a hash of the deployed
   mod's script folders. If `save games/te_qa_fixture_<key>.v3` is missing, make it as in
   § 3.6 (about 90 seconds) and rename it. Keep the two most recent fixtures; each is
   about 133 MB and shows in the owner's load menu under its `te_qa_` name.
2. **Session.** Launch `-debug_mode -script_debugger -loadsave=<fixture>`. An owner's save
   can be named instead; it is snapshotted first and cannot be overwritten, since the
   console cannot save.
3. **Ready** means a console command has made a round trip: the console key is sent,
   `select_event_option list` is typed, and the command shows in `console_history.txt`.
   Retry the console key on no answer; give up, with a screenshot in the report, after a
   timeout.
4. **Country.** `tag <TAG>`, confirmed by its "Now Playing" reply.

Whether time can then advance without clicking Start is assumption A2.

### 5.6 Commands in

All input is console text. For each command the driver:

1. checks that the foreground window is the game's own handle. If it is not, the helper
   may take the foreground back, with one exception: if there has been keyboard or mouse
   input that the helper did not send within the last 30 seconds, someone is at the
   machine, and it waits instead, retrying for up to two minutes. If the game still is not
   in front (a locked desktop, the owner at work in another window), the step fails: the
   game is left running and paused, nothing is typed, and the session asks the owner or
   calls `stop`;
2. types the command and Enter;
3. waits for it in `console_history.txt` (arrival), then for its `console_success` or
   `console_failure` line in `debug.log` (result), forcing the log out as in § 5.7.

The console is opened once and left open. The driver never sends the console key
without then confirming a round trip, since the key toggles.

### 5.7 Results out

- **Log tail.** From launch the driver follows `debug.log` and `error.log` continuously,
  across rotation, and keeps its own copy for the run. Lines are attributed to a step by
  the driver's markers around it.
- **Flushing.** After a command whose reply is needed, the driver causes at least 4 KB of
  log output. The verified way is `help ndefines.ngui`; a block of padding `debug_log`
  lines from the carrier would be quieter (assumption A5).
- **Reads.** The driver sets a breakpoint on the carrier's first line, fires the carrier,
  and, with the game stopped there, evaluates each trigger and value the session asked
  for, then continues. This needs no reload and no flush. Values are asked through the
  played country's tag (`c:FRA.<value>`), the form that was verified; that named mod
  script values and variables read the same way is assumption A4.
- **Errors.** New `error.log` lines during a step are reported with it, less the
  validator burst that each debugger evaluation causes (§ 3.5) and less what the log
  triage registries already explain.
- **Screenshots** on request and on every timeout, for the session to look at.

### 5.8 The verbs

Names are the builder's; the set is the design.

| Verb | Does |
|---|---|
| `doctor` | Checks the machine: paths, Windows Python, an unlocked desktop, `nvidia-smi`, the backup root. Launches nothing |
| `start --permission … [--save NAME] [--as TAG] [--setup FILE …]` | Gate, snapshot, overlay, fixture if needed, launch, ready, `tag` |
| `console "<text>"` | One console command, with its reply |
| `run-setup <name>` | Fires the carrier for a prepared effect |
| `events` | `select_event_option list`, parsed |
| `pick <index> [<event>]` | Selects an option; resolves an event id or name to the numeric id from `events` |
| `read "<expr>" …` | Triggers and values through the debugger |
| `advance <days>` | Lets at least that many days pass and reports the date reached (needs A2) |
| `tag <TAG>` | Changes the played country |
| `shot` | Window screenshot, returns the path |
| `try-event <event> --as TAG [--setup NAME] --read "<expr>" …` | The owner's first check, composed: for each option in turn, run the setup, fire the event, read, pick that option, read again; one table in the report |
| `stop` | Ends the game it started, compares and restores, closes the report |

**State between checks.** The console cannot load a save, so a clean game costs a
relaunch of about 2 minutes. Version 1's policy: checks in one session share the game's
state and the report says so; `try-event` re-runs the setup before each option; a check
that needs a clean game asks for `--fresh`, which relaunches from the fixture. Testing
each option on a different country (`--as` per option) isolates them at no cost where the
event allows it.

Most of the mod's events carry a `cooldown` and many a once-only variable, so firing one
a second time on the same country may do nothing. If A6 holds (console `event` ignores
`trigger` and `cooldown`), `try-event` fires with console `event` and the shared game
stands. If it does not, `try-event`'s default becomes a different country per option
where the session names enough of them, and a relaunch per option otherwise; either way
it confirms before each pick that the event is pending and reports "did not fire" as a
result of its own, never as a pass.

### 5.9 The report

One folder per run under the backup root, with a short text summary a session reads
first: the permission text, GPU reading, game version, playset, the deployed build's
drift (how many files differ from the session's checkout and from `origin/main`), every
step with its times, replies, readouts and new errors, the screenshots, the driver's log
copy, and what the restore did. The driver prints the summary's path when it stops.

## 6. The first check, walked through

"Fire `decolonization_events.17` as France, pick each option, confirm the effects."

1. The session reads the event. It saves its own scopes in `immediate`, from a
   neighbouring country that holds `recently_decolonized`; its `trigger` also wants that
   variable on France, and it has a `cooldown` and a once-only variable. So the setup
   effect sets `recently_decolonized` on France and on one neighbour, and clears the
   once-only variable and the two border-dispute modifiers so the event can fire again.
   The session lists what to read: `has_modifier = border_dispute_resolved_modifier`,
   `c:FRA.infamy`, a relations value.
2. `try-event decolonization_events.17 --as FRA --setup border_dispute --read …`.
3. The driver passes the gate, snapshots, generates the overlay, makes or reuses the
   fixture, launches, and tags France.
4. For option 0: run the setup, confirm the event is pending and has the expected number
   of options, read, pick 0, read, collect new errors. Then options 1 and 2.
5. `stop`: the game closes, the owner's files are compared and restored, and the report
   has one row per option with the before and after of each read.

This event is a hard case on purpose. The acceptance test of version 1 (§ 8) may use a
simpler one if A6 fails.

## 7. Assumptions to settle first

The plan's first task is one permitted session of a few launches that settles these and
records the captures § 11 says are missing. None may be settled by launching outside the rule in § 5.2.

| # | Assumed | If false |
|---|---|---|
| A1 | An event fired by `trigger_event` from the carrier's effect is pending and selectable at once, paused, with the scopes the carrier saved | Advance one day first (needs A2). Events that need no saved scopes use console `event` either way |
| A2 | After `tag` on the loaded fixture's country-select screen, time advances with the pause and speed keys | One click on that screen's Start button, placed from the window's size and confirmed by screenshot, done once per session; or a fixture the owner saves by hand |
| A3 | A second mod folder added to `content_load.json` loads on a direct launch, including its events and its `tools/scripted_tests/` | Generate the overlay into the deploy folder under `te_qa_*` names and exclude those names from `deploy.sh`'s `--delete` |
| A4 | The debugger evaluates named mod script values and variables through `c:TAG.` (verified only for `c:FRA.gdp` and for triggers) | The overlay generates one readout line per value (`debug_log` with `ScriptValue(...)`), read from the log after a flush |
| A5 | About 4 KB of `debug_log` padding from the carrier flushes the log as the console's help listing does | Keep the help listing |
| A6 | Console `event <id>` fires an event whatever its `trigger` and `cooldown` say (the probe event had neither) | The setup effect makes the trigger true and clears what the last firing left; where a cooldown still blocks it, one country or one relaunch per option (§ 5.8) |

## 8. Phases

1. **Version 1**: §§ 5.1–5.9, with `try-event` as its acceptance test on one real mod
   event, and the skill.
2. **Check files**: a small declarative format kept in the repo, one file per system,
   run in a batch; a play-test list's "fire and look" items move into it.
3. **Unattended runs**: `-handsoff -run_until` soak runs gathering the mod's
   `TE_SELF_CHECK` lines and the per-day timing file, and the engine's scripted tests once
   their result file is understood.
4. **Choosing the build**: testing a branch by syncing it to a second mod folder and
   pointing the run's playset at that, so the owner's deploy folder is never touched.

## 9. The designer's calls worth checking

- **The default playset is this mod plus the overlay only**, not the owner's current one.
- **Version 1 tests the deploy folder as it stands** and reports drift, instead of
  deploying a chosen commit.
- **GPU "heavy" is 50% mean utilization or more than half the memory in use.**
- **A required `--permission` text** as the tool's half of the permission rule.
- **Fixtures sit in the owner's `save games/`** as `te_qa_fixture_*`, two kept.
- **Reads go through the debugger**, with generated log readouts as the fallback.
- **Shared state between checks by default**, `--fresh` on request.
- **The Windows helper is Python**, not the PowerShell the probes used.
- **The helper takes the keyboard back for the game** unless someone has typed or moved
  the mouse in the last 30 seconds; then it waits, and fails the step after two minutes.
- **The owner's logs are put back** after a run, so their next log triage sees their own
  last session; the run's logs are in its report.
- **A dead run's restore is abandoned, not forced**, once the owner has played since; its
  snapshot is held.

## 10. Left to the builder

File and verb names; the driver's service transport; how the helper is kept alive across
calls; the snapshot store's layout, within § 5.3's rules; the readiness and timeout
figures; how `advance` reads the date; how an event name is matched to a pending numeric
id when two instances of one event are pending; the report's exact shape; whether the log
triage registries are imported or their output parsed.

## 11. Tests and docs the build owes

- Unit tests for every part against fakes: a fake helper, recorded log files including a
  rotation and a buffered tail, a fake debugger socket, a temporary user-data folder for
  snapshot, restore and the unfinished-run recovery. Live tests exist but run only when
  asked for by name on a machine with the game. The probe scripts, the probe's mod files
  and three captures (a debugger session, the console's command list, the console lines of
  a session) are in `docs/testing/game_qa_probe/`; its README lists what was not captured.
- `.claude/skills/game-qa/SKILL.md`, a row in `CLAUDE.md`'s rules table, and the tool's
  entry in `docs/guides/python_tools.md`, replacing the stopgap section "Driving the game
  from a session" that this design adds there for sessions working by hand.
- The engine facts of § 3 are recorded with this design in
  `docs/guides/scripting_best_practices.md` § "The console can pick event options and
  switch country; it cannot run a script file or save".

Player guide: no player-facing change.
