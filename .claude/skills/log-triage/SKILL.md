---
description: Triage Victoria 3 game logs in this mod repo. One script snapshots every log family and generation and reports what no registry entry explains; then decide mod, vanilla or third party for each finding, fix the mod's, register the rest, read the self-checks, and record what was learned. Use whenever investigating crashes, in-game bugs, missing content, modifier no-ops, journal entries that don't surface, a probe or self-check a PR is waiting on, or after a game session ends.
---

# Log triage skill

## When to use

- User reports an in-game bug, crash, or modded content not appearing.
- A modifier, journal entry, decree, or event doesn't behave as expected.
- After a game session, or after re-launching with mod changes.
- A PR is waiting on a `TE_SELF_CHECK` or probe line.
- User asks "what's broken in the logs?" or "did my edit break anything?".

## 1. Snapshot and report

```bash
python3 scripts/analysis/log_triage.py --out "<scratchpad>/logs-1" > "<scratchpad>/triage-1.txt"
```

About four seconds, no server, safe while the game runs. It copies every generation of `debug`, `error`, `game`, `gui`, `dedicated_server`, `system` and `custom_automated_stats` (by exact name, mtimes kept) and prints one report over all of them. Do this before anything else: the logs rotate at 524 KB, six generations a family, so a flood or the owner's next launch erases what you were reading. Afterwards `--snapshot <dir>` reports on the same files again, which is how you check a registry edit.

From a worktree the script reads that worktree's registries and the main checkout's mod files, which is what you want. Don't `POST /reload` from a worktree.

**Start with debug.log's view of things, but read all of it.** `error.log` holds script errors and some load-time validation that debug.log lacks; `game.log` repeats error.log's script errors and rotates later; `gui.log` holds layout and template lines and is only written out when the game quits. The report merges them and counts a line once.

## 2. Read the report, section by section

| Section | What it tells you | What to do |
|---|---|---|
| **Launches** | Each launch in the logs: start, exe version, new game or loaded save, game dates, the playset, and how much of each family survives | A family "from HH:MM:SS" has lost that launch's load-time errors; only a fresh launch shows them (and only a new game runs `common/history/`). A mod-off launch is where vanilla's own errors show. If it says commits reached `origin/main` since, see § 3 step 3 |
| **Registry** | The registries' loader warnings; `DRIFT`: a registered signature logged from a cpp line no entry names | Fix the warnings. For DRIFT add the new `- source:` line to the entry and keep the old one |
| **Untagged** | Every line no entry explains, grouped by exact message, mod-framed ones first | Each is a finding until explained: § 3 |
| **Watch list** | Lines an entry tags and leaves visible, with its `check:` | Do the check every time and say what it showed |
| **Hidden by a vanilla entry, with a mod file in the stack** | Lines the registry hides although a mod file is in their stack | `NOT REVIEWED` is how a hidden mod error looks. Read the lines; narrow the entry or add `- reviewed: mod frame, <why>` |
| **Volume** | The largest classes, hidden or not | A flood is what rotates the logs. A registered class that has grown is a claim to re-check, not a fact |
| **Self-checks and traces** | Every `TE_SELF_CHECK` by name and verdict, the play-test list that waits for it, `START` with no verdict, `LOST` probe lines | A first `OK` or `BROKEN` goes into the play-test list named. `BROKEN`, a lone `START` and `LOST`: § 4 |
| **Crashes** | Crash folders newer than the oldest launch | `python3 scripts/lessons.py crash`, then the crash folder's own frozen `logs/` |

Per finding the report gives the launch, wall-clock and game date, the lines of the file (never folded together), a burst's rate, how much of it came while the game was paused, and for a line that names no file what else was logged in the same second (`near:`). A burst while paused, or at hundreds of lines a second, is a tooltip or panel being drawn, not the simulation running.

## 3. For each untagged finding

1. **Search what earlier triages learned:** `python3 scripts/lessons.py <cpp source or words of the message>`. The answer is often already there, with the trap that goes with it.
2. **Whose is it?**
   - *A mod file in the stack*: the mod's, unless the first frame (`Script location:`) is a third-party mod's file. error.log lists the whole call stack.
   - *Vanilla files only*: usually vanilla's, but check the three ways the mod causes an error at a vanilla line: the mod overrides that file whole (`ls <path>` in the repo), a mod script-value override is read there (`git grep -n "^<name> = {" common/script_values`), or a mod feature is the first to show vanilla content nothing showed before.
   - *In neither the mod nor vanilla*: a Workshop mod. Find it under `steamapps/workshop/content/529340/`; if it floods, add its file names to `EXTERNAL_MOD_SOURCE_FILES` in `game_log_reader.py`.
   - *No file named* (an assert, a GUI or loc data error): read the `near:` lines. A `Data error in loc string '<key>'` line names the string; a script error or `TE_` trace in the same second usually names the cause. A `MOD GUI:` line under the finding means a generic source-only vanilla entry matches it and the mod's own GUI draws the key or reads the data type it names: read the files listed for a widget shown outside the window that holds that context. A type many mod files read (`Country`) can also be vanilla's own line; if it is, register or watch it with a signature that reaches into the quoted part (`wanted context of type 'Country' for 'Country.GetFoo`), on the same `- source:`. Such an entry keeps the line wherever it sits; only the generic entries give way. Two entries of the same cascade are not covered and still hide a mod GUI's lines, so count their payloads by hand: `pdx_data_callstack.cpp:325` (`New data types does not contain a '<Type>'`) and `pdx_data_localize.cpp:136` / `:151` (`Data error in loc string '<key>'`).
3. **Is it already fixed?** The logs are the deployed build's. If `main` has moved since the launch, `git log --oneline --since="<launch start>" origin/main -- <file>`; and check open PRs: `gh pr list --state open --limit 60 --json number,title,files -q '.[] | select(any(.files[]; .path|test("<file>"))) | "\(.number) \(.title)"'`.
4. **Then one of:**
   - **Fix it** (the mod's). If the engine was silent about the cause, add the test or audit that would have caught it. Out of scope for this session: file a GitHub issue with the evidence and a proposed fix.
   - **Register it** (vanilla's, or mod noise that is tracked): § 5.
   - **Watch it** (could be either, and the line can't say): a watch-list entry with its check.
   - Leave nothing unexplained and unrecorded: the next triage will pay for it again.

## 4. Self-checks, probes, saves

- A probe answers through which branch fired; its printed numbers may be blank (`ROOT` and saved scopes print nothing in `debug_log`).
- Before reporting `BROKEN`, rule out the cases its branch can't tell apart, and check the play-test list's row for what it prescribes.
- A `START` that never gets its verdict is a dead path until the save says otherwise.
- `LOST`: the engine dropped the line (a bad accessor). Fix the string and re-arm a once-a-game check by renaming its marker.
- **The logs are not the game's state.** A system that silently does nothing logs nothing, an assert naming one country can stand for a hundred, and a registry entry that says "harmless" is a claim about the save. Read the save: `scripts/analysis/save_country_probe.py` (`--var`, `--states`, `--laws`, `--diff`). Copy autosaves by mtime; they rotate.

## 5. Registering a line

Where: a vanilla bug with a script path → `docs/vanilla/vanilla_known_bugs.md` § "Script errors observed"; an engine line with no path → § "Engine noise" with `- source:`; the mod's own tracked noise → `docs/audits/mod_known_noise.md` with `- tracked:` to `open_issues.md`; could be either side's → the watch list at the end of `vanilla_known_bugs.md`, with `- check:`. The top of `vanilla_known_bugs.md` gives the entry format.

- Heading: `` ### `path/to/file.txt:12, 40` — paraphrased title ``. A backticked `.txt`/`.gui`/`.yml` path anywhere in the entry becomes an anchor, so write other paths plain. A `.dds` can't anchor: use `- source:`.
- Signature lines are message text, taken from the raw line (`repr`), never a bare path and never a `<placeholder>`.
- `- stack: vanilla only` whenever mod script can reach the vanilla file (an AI strategy, an on_action, a scripted trigger).
- Say in the body how you know it is vanilla's, with the count and the date. If you didn't check, say that instead.
- **Verify:** run the report again on the same snapshot. The finding is gone, the "Hidden … mod file" section has nothing new, and the Registry section has no warning. For a signature change to an existing entry, also `scripts/analysis/registry_retag_diff.py diff` against an archived run. `POST /validate/registries` adds the helper-anchor check, which needs the game files.

## 6. After a fix

A fix shows in the logs only at the next launch (and a load-time one only in a launch whose start survives). Run the report again then and compare the Untagged sections; `/validate/engine-coverage` and the audits answer sooner for parse-time problems. A fix that silences one load-time class can open another at the same file, so compare by file, not by message.

## The server's view

`/logs/*` on the mod state server (port 8950) serves the same tagging for one generation at a time, and is the place for a quick filtered query:

```bash
curl -s "http://localhost:8950/logs/debug?dedupe=true&mod_only=unknown&vanilla_bugs=hide&mod_noise=hide&debug_log=hide"
curl -s "http://localhost:8950/logs/debug/diff?against=1&mod_only=unknown&vanilla_bugs=hide&mod_noise=hide&debug_log=hide"
curl -s "http://localhost:8950/logs/debug?debug_log=only&mod_only=true&q=TE_&dedupe=true"
```

Families: `error`, `debug`, `game`, `gui`, `graphics`, `event_scopes`, `dedicated_server`; `?gen=N` for a backup generation; `q=`, `file=`, `source=`, `category=`, `since=` filter. Give every hand-built query all four of `mod_only=unknown&vanilla_bugs=hide&mod_noise=hide&debug_log=hide`, or registered lines come back looking new. Its dedupe folds digits, so two lines of one file show as one: count sites from the report. `POST /reload?engine_only=true` re-reads the logs and registries in about a second.

## Category playbook

`SOURCE_CATEGORY_PREFIX` / `SOURCE_CATEGORY_FILE` / `MESSAGE_CATEGORY_BY_FILE` in `game_log_reader.py` are the source of truth for category names.

| Category | What it usually means | Where to look |
|---|---|---|
| `script_parse_error` | Typo, vanilla rename, unregistered modifier, or unknown trigger. One usually cascades into "Unknown effect/trigger" lines below it in the file: fix the first, then look again | `docs/guides/vanilla_patch_runbook.md` § Known vanilla renames; `/modifier-search?q=` |
| `inject_to_missing` | Vanilla renamed or removed an `INJECT:` target | Same runbook |
| `duplicated_key` | Top-level entity collision | Convert the mod's declaration to `INJECT:` |
| `inconsistent_trigger_scope` / `inconsistent_effect_scope` | Wrong scope for the trigger or effect | `/engine-docs/triggers`, `/engine-docs/effects` |
| `used_but_never_set` | Load-time validator: a variable or event target read somewhere and set nowhere the engine can see | A name built from a parameter for values that never exist, a typo, or dead code kept for an old save (1.15 loads none: remove it) |
| `missing_file` / `missing_texture_for_entity` | An asset not found | Substitute or remove the reference |
| `dds_dimensions` | DDS not a multiple of 4 | Visual only; needs a re-export |
| `gui_parse_error` / `gui_widget_error` | GUI script error | `docs/guides/gui_modding_guide.md` |
| `debug_log` | Script `debug_log` output, the mod's `TE_` traces and vanilla's "Party Created" lines | Not errors; the report's Self-checks section reads them |
| `other` with `should be in utf8-bom encoding` | A script file without its BOM | A full `POST /reload` fixes it (`bom_normalizer.py`); a generator that writes without one needs `encoding="utf-8-sig"` |

What never reaches a log: an invalid modifier name (validate with `/modifier-search?q=`), a missing loc key (the player sees the raw key; go to the key family and `loc_coverage_audit`), and a system that does the wrong thing quietly (§ 4).

## Lessons

`.claude/skills/log-triage/lessons.md` holds what earlier triages learned, by topic, searchable with `scripts/lessons.py`. Before ending a log-triage turn, ask whether the next Claude would rediscover something from scratch. If so, write it in exactly one place:

- **Reading logs, the registries, the triage tools** → a new `###` section in `lessons.md` (heading = the rule, with the date)
- **A step a script could do** → `scripts/analysis/log_triage.py`, and a test in `test_log_triage.py`
- **What one vanilla message means** → its entry in `docs/vanilla/vanilla_known_bugs.md`
- **Engine syntax, scope rule, scripting gotcha** → `docs/guides/scripting_best_practices.md`
- **A first self-check verdict, or anything only the game showed** → that system's list in `docs/testing/`
