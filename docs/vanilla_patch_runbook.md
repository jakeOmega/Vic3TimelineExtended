# Vanilla patch update runbook

End-to-end workflow for updating Vic3TimelineExtended for a new vanilla Victoria 3 patch (e.g. 1.12.4 → 1.13). Follow in order — earlier steps unlock later ones.

## 0. Prerequisites

- Local clone of vanilla at `~/src/vic3` (full git history; the prior version is in git history).
- Mod state server runnable: `python3 mod_state_server.py` (use `python3`, not `python`, on this system).
- The mod loads cleanly on the prior vanilla (i.e. before starting the migration, the mod is in a known-good state).

## 1. Snapshot the current mod (BEFORE applying patch)

```bash
python3 scripts/snapshot_balance.py > docs/balance_snapshot.json
git add docs/balance_snapshot.json
git commit -m "snapshot mod balance before <vanilla-version> migration"
```

Captures key gameplay values (combat units, ship types, late-era tech modifiers, law modifiers) so you can verify the *intent* survives any rebalancing later. Without this, post-patch rebalancing requires recall ("what were the pre-patch hypersonic platform stats again?").

## 2. Identify the diff baselines

In `~/src/vic3`:

```bash
git -C ~/src/vic3 log --oneline | head -20
```

Find the commit that bumped to the new version (e.g. "v1.13"). Its parent is the prior version baseline. Save these as `OLD_REF` and `NEW_REF`.

## 3. Engine-doc diff

Compare `docs/modifiers.log`, `docs/effects.log`, `docs/triggers.log`, `docs/on_actions.log` between `OLD_REF` and `NEW_REF` in vanilla. Categorize:

- **Removed**: identifiers that existed in OLD but not NEW. These break the mod hardest. Examples from 1.13: `country_convoys_capacity_*`, `unit_navy_*`, `unit_blockade_*`, `state_building_naval_base_max_level_add`, `military_formation_movement_speed_mult`, `is_ruler`/`is_heir` triggers, `country_max_declared_interests_*`.
- **Renamed**: re-named pairs (e.g. `has_role` → `has_role_of_type`). Identify by name similarity.
- **Semantics changed**: same name, different meaning. Watch for `relative_*` triggers and similar.
- **Added**: useful new modifiers/effects/triggers the mod might want to leverage.

You can use the mod-state server validator as a gating signal: after preliminary edits, `curl http://localhost:8950/validate/engine-coverage` returns the modifier names the mod uses that are no longer recognized.

### Known vanilla renames (cumulative across patches)

When `debug.log` shows `Unexpected token: <name>` or `inject/replace to a non-existing entry: <name>`, check this table before grepping vanilla. Each entry is a vanilla rename the mod has been bitten by. Add new ones as you find them.

| Old name | New name | Where it bites | Notes |
|---|---|---|---|
| `should_be_pinned_by_default` | `should_be_pinned_by_default_uninvolved_or_context` | Journal entry top-level field | Renamed sometime around 1.13. Symptom: `Unexpected token: should_be_pinned_by_default` in debug.log. Bulk rename: `for f in $(grep -rl "should_be_pinned_by_default[^_]" common/journal_entries/); do sed -i 's/should_be_pinned_by_default\([^_]\)/should_be_pinned_by_default_uninvolved_or_context\1/g' "$f"; done` |
| `telecommunications` (tech) | `telephone` (tech) | `INJECT:` targets in `common/technology/technologies/modified.txt` | Vanilla split the old umbrella tech. The intelligence-capacity slot the mod wanted lives on `telephone`. |
| `canning` (tech) | `canneries` (tech) | `INJECT:` targets in `common/technology/technologies/modified.txt` | `vacuum_canning` still exists; only the early-era `canning` was renamed. |
| `has_role` (trigger) | `has_role_of_type` (trigger) | All character-role checks | Bulk-replaceable. |

### Symptoms-to-cause cheat sheet

- `Unknown modifier type: X` (debug.log, `script_parse_error`) → either a vanilla rename (check table above) or a missing dynamic-modifier-type registration in `common/modifier_type_definitions/`. Vanilla only auto-registers SOME axis combos for ship_battle / ship_construction / goods_input/output patterns — modded ships, modded goods, AND vanilla ship/good types the mod uses on a NEW axis all need explicit registration. See `docs/scripting_best_practices.md` § "Dynamic Modifier Type Definitions".
- `Unexpected token: X` → renamed top-level field (table above) or invalid syntax. JE pinning fields and law fields tend to drift across patches.
- `Unknown trigger type: X` → renamed/removed trigger or event-target. Validate via `curl 'http://localhost:8950/engine-docs/triggers?q='` and `…/engine-docs/event-targets?q=`.
- `Duplicated key X will not be created` → mod redeclared a top-level entity vanilla owns. Switch to `INJECT:X = { ... }` (see `docs/scripting_best_practices.md` § "Top-Level Database Collisions").
- `inject/replace to a non-existing entry: X` → vanilla renamed or removed `X`. Use the table or the symptoms-to-cause grep workflow.
- `Value of wrong type in '<file>:<line>'. Got value of type 'none'` → script value or trigger reading an uninitialized `global_var:` / `variable:`. Initialize from `on_game_started` (see `docs/scripting_best_practices.md` § "Global Variable Initialization Timing").

## 4. Re-run all auto-generators

The auto-generators read vanilla and emit mod files. Re-running them after a vanilla patch picks up vanilla's content changes for free. Run in this order:

```bash
python3 apply_ideologies.py                          # common/ideologies/modified.txt
python3 ig_feminism.py                               # common/interest_groups/00_*.txt (8 files)
python3 pop_needs_curves.py                          # common/buy_packages/00_buy_packages.txt
python3 resources.py                                 # map_data/state_regions/*.txt
python3 scripts/generators/gen_formable_regions.py   # common/geographic_regions/te_formable_regions_generated.txt
```

If the vanilla map changed (states removed/renamed/split), edit `deposits_config.json` to point old keys at successors **before** running `resources.py`. See `docs/auto_generated_files.md` for the full ownership table.

`gen_formable_regions.py` reads vanilla `common/strategic_regions/*.txt` and re-expands the four EU/Africa/N.America/Earth formable regions to explicit state lists — re-run if vanilla rebalances strategic regions or renames states. The script also fails loudly if a configured strategic region disappears, which is the signal to update its inline config.

## 5. GUI override re-merge

For each mod-overridden `.gui` file, run a 3-way merge with vanilla's pre- and post-patch versions. See `docs/gui_modding_guide.md` § "GUI 3-way merge across vanilla patches" for the exact `git merge-file` command. In the 1.13 migration this resolved 14 of 17 GUI overrides cleanly with 5 manual conflicts.

If vanilla deleted a mod-overridden GUI file (vanilla 1.13 deleted `commander_panel.gui`), delete the mod's override too — keep an issue open to re-apply mod customizations elsewhere if the panel content moved.

## 6. Migrate breakages identified in step 3

Walk the validator's reported unknowns. For each:

- **Removed modifier with a clear successor**: rename it in mod files. Bulk grep:
  ```bash
  grep -rln "<old_name>" --include="*.txt" common/ events/
  ```
- **Removed mechanic with no equivalent**: delete the references and accept some loss of mod functionality, OR re-implement using new vanilla primitives (a Phase B-style task; beyond the scope of "make it load").
- **Renamed trigger** (e.g. `has_role` → `has_role_of_type`): bulk replace with `Edit replace_all=true`. Watch for partial-match collisions.
- **Strategic-region consolidation**: sweep mod for `sr:region_*` references; map old → new. The 1.13 mapping is in commit history if needed.
- **Map state removed/renamed**: handled in step 4 via `deposits_config.json` for resources, plus targeted edits for any tourism / wonder / company / event references using `s:STATE_*`.

After each batch of edits: `curl -X POST http://localhost:8950/reload?engine_only=true` then `curl http://localhost:8950/validate/engine-coverage` to verify removed-modifier count drops.

## 7. Special-case: combat units / ship types

Patches sometimes add new entity TYPES (1.13 added `ship_types/`, replacing the old `combat_unit_types` naval section). The migration is not a rename — it's a system replacement. Strip the old entries first to make the mod load, then port the entries to the new framework as a follow-up.

If the mod has late-era ships beyond vanilla's tier (the case here: nuclear submarine, hypersonic platform, etc.), preserve their progression curve from the snapshot in step 1. Pre-1.13 mod's progression was roughly 2-3× per era (battleship 100 → fleet carrier 300 → nuclear supercarrier 700 → arsenal ship 1800 → hypersonic 4000). Match this scaling against vanilla's new top-tier baseline (super_dreadnought).

## 8. Triage runtime errors

Load the game with the migrated mod, run an observer game for a decade or so, then triage the error log:

```bash
curl -s http://localhost:8950/logs/error?dedupe=true | python3 -m json.tool
```

For each entry:

1. Locate file and line.
2. If the file is a vanilla path that doesn't exist in mod, it's a vanilla bug. Cross-reference `docs/vanilla_known_bugs.md` and add new entries as discovered.
3. If the file is mod-owned (or mod-auto-generated), trace the source.

## 8b. Refresh `docs/vanilla_economy_reference.md`

That file captures vanilla economic concepts (pops/IP, markets/MAPI, companies, power blocs, naval economy) for AI-agent context. It carries a "Last verified against vanilla: X" banner. After the migration:

- Update the banner to the new vanilla version.
- Skim the doc against this patch's release notes and the engine-doc diff (step 3). Edit any section where 1.x semantics changed — new resource types, removed mechanics, restructured ownership, new principle families, ship-designer changes, etc.
- Don't fork a "1.14 economy" copy. Overwrite. Old versions live in git history.

If nothing changed, just bump the banner — that's the signal to future agents that the doc has been actively re-validated, not just stale.

## 9. Validator regression bar

Final validator run:

```bash
curl -s "http://localhost:8950/validate/engine-coverage?filter=vanilla_breakages"
```

(See `docs/python_tools.md` for the filter; in absence of the filter, manually classify the 29-or-so unknown entries against `common/modifier_type_definitions/`.)

The bar is **0 vanilla breakages**. Mod-defined custom modifier types (`country_sr_*`, `country_covert_*`, `cultural_hegemony_*`, etc.) reported as "unknown" by the validator are pre-existing limitations of the validator, not real breakages.

## 10. Verify in-game

- Game loads to main menu without `error.log` spam.
- 1836 starts smoke-test (Britain, France, Japan, one minor): no error spam in first month, all major mod systems' JEs appear.
- Late-era starts smoke-test (1936 if start dates allow): mod's modern naval ships build, fight, upgrade.
- Open every overridden GUI panel and confirm layout is sane.
- Run validator one last time after a few minutes of in-game activity.
