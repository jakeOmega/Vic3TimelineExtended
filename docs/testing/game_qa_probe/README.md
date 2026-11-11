# In-game QA harness: probe files (2026-11-10)

What the eight probe launches behind
`docs/superpowers/specs/2026-11-10-in-game-qa-harness-design.md` § 3 were run with, kept so
the builder does not start from prose. Throwaway code: it shows that each call works, not
how the harness should be written. Nothing here is deployed or loaded by the mod.

| Path | What it is |
|---|---|
| `powershell/lib.ps1` | The Win32 calls: `SendInput` by scancode and as Unicode text, foreground window, client rectangle, click |
| `powershell/launch.ps1` | Starts `victoria3.exe` with arguments and prints its process id |
| `powershell/keys.ps1` | A step list for the game window: `tick` (console key), `t:<text>`, `enter`, `space`, `w:<ms>` |
| `powershell/gshot.ps1`, `shot.ps1` | Screenshot of the game's client area, or of the whole desktop |
| `powershell/win.ps1` | Foreground window, the game's window and the ports it listens on |
| `powershell/dap.ps1`, `dap2.ps1` | Debug-adapter clients: a request list, and breakpoint, wait for the stop, scopes, evaluate, continue |
| `overlay/events/te_qa_probe_events.txt` | The hidden carrier event and a visible event with three options that each log a line |
| `overlay/common/scripted_effects/te_qa_probe_effects.txt` | The effect the carrier calls |
| `overlay/tools/scripted_tests/te_qa_probe.txt` | The scripted test that fails on day 2 and so leaves a fresh save |
| `captures/debugger_transcript.txt` | One debugger session, requests and replies, with three of the 3,779 `output` events kept as samples |
| `captures/console_commands.txt` | What `help` printed: every console command and tweakable, without the `NDefines` names |
| `captures/debug_log_console_lines.txt` | The `console.cpp` and `debug_log` lines of the last session: `tag`, `event`, `select_event_option` and their replies |
| `overlay/events/te_qa_probe_assumptions_events.txt` | The live session's events: a false trigger, a cooldown, an event that reads a scope its caller saved, the carrier that triggers it, a padding event |
| `overlay/common/script_values/te_qa_probe_values.txt` | A script value over a variable, for the debugger read test |
| `overlay/.metadata/metadata.json` | What made the overlay a mod folder of its own |
| `live_session/journal.py` | Recorded the run in the snapshot's journal by hand (the `watch` verb did not exist yet) |
| `live_session/helper_proof.py`, `helper_idle.py` | The Windows helper proven against the running game: adopt, focus, keys, screenshot, debugger relay, kill; and the idle-time readings |
| `captures/live_session_early_lines.txt`, `live_session_lines.txt` | The live session's console and probe lines (the early ones from the terminal output, since their log generations rotated out) |
| `captures/debugger_evaluations_2026-11-10.txt` | Every expression evaluated at the breakpoint, with its reply |
| `captures/log_rotation_2026-11-10.txt` | Inode, size and first bytes of each generation before and after a rotation; the padding flush |
| `captures/content_load_with_overlay.json` | The playset file with the overlay added as a fifth mod folder |

For the first eight probes the overlay files were copied into the deployed mod folder and
removed afterwards. For the live session of 2026-11-10 (two launches, 16:06–16:16) the overlay was
a mod folder of its own, `mod/te_qa_overlay/`, added to `content_load.json`; the owner's files
were snapshotted and restored with `python3 -m game_qa`. A Windows user name in a captured path
is written `<winuser>`.

Not captured: the raw bytes of a rotation as it happens (the inode table in
`captures/log_rotation_2026-11-10.txt` records what the follower needs, and the session's raw
logs went back out of the game's folder with the restore), and a buffered tail before and after
a flush as files (the sizes are in the same capture).
