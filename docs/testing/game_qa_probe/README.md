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

The overlay files were copied into the deployed mod folder for the probes and removed
afterwards. A Windows user name in a captured path is written `<winuser>`.

Not captured, and owed by the builder's first live session: a `debug.log` rotation as it
happens, a buffered tail before and after a flush, and a `content_load.json` with a second
mod folder added.
