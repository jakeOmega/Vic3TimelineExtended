# Vic3TimelineExtended
Mod for Victoria 3 extending timeline

## Setting up on a new machine

```bash
git clone <repo-url> Vic3TimelineExtended
cd Vic3TimelineExtended
python3 scripts/setup.py
```

The setup script creates a `.venv`, installs the Python tooling deps, then auto-detects (or prompts for) the Steam install of Victoria 3, your Paradox documents folder, and the deploy target. It writes a gitignored `paths.local.json` with the results and runs a dry-run deploy to verify everything resolves. Re-run any time paths move.

WSL is the supported primary platform — the autodetector reads Steam's `libraryfolders.vdf` and the Windows username via `cmd.exe`. On native Linux or Windows the script falls through to prompts.

For vanilla-vs-mod disambiguation, the tooling expects a vanilla `script_docs` snapshot at the path you give for `vanilla_snapshot_docs_path` (default `~/src/vic3/docs/`). Setup warns if it's missing and prints the manual refresh workflow (launch vanilla unmodded → `script_docs` in the in-game console → copy logs).

Per-path env-var overrides also work, useful for one-off invocations: `VIC3_BASE_GAME`, `VIC3_MOD_DEPLOY_TARGET`, `VIC3_VANILLA_DOCS_SNAPSHOT`, `VIC3_VANILLA_REPO`, `VIC3_VANILLA_DOCS_RUNTIME`, `VIC3_GAME_LOGS`. See `path_constants.py` for the resolution order.

## Game Rules

The following mod systems can be toggled via game rules at game setup:

### Banking System (Default: Enabled)
Controls the banking cycle journal entry and financial regulation system. When enabled, financial regulation laws provide banking intervention tools, momentum effects, and crash chance modifiers that drive the banking cycle. When disabled, the journal entry does not appear, but financial regulation laws still provide standard economic effects (construction cost reductions, infrastructure bonuses, and other non-banking modifiers).

### Global Warming (Default: Enabled)
Controls the global warming journal entry and greenhouse gas tracking system. When enabled, greenhouse gas emissions are tracked globally and climate policies affect temperature rise. When disabled, the journal entry does not appear and emissions tracking is inactive, but environmental policies and events still provide pollution reduction effects as an alternative to greenhouse gas effects.

### World War (Default: Disabled)
Controls the world war journal entry for great powers. When enabled, ideological tensions between great powers can escalate into a global conflict with leadup, active war, and post-war phases. When disabled, the journal entry does not appear and world war events will not fire. World war buttons use direct technology checks (Combined Arms, Mass Media) rather than boolean modifier types.

## Credits

The construction-market subsystem (files prefixed `te_construction_market_*` in `common/` and `events/`, plus the integration in `gui/construction_panel.gui`) is based on the third-party **Free Market Construction** mod. Credit and thanks to that mod's author.
