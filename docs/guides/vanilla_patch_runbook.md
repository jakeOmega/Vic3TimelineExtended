# Vanilla patch update runbook

End-to-end workflow for updating Vic3TimelineExtended for a new vanilla Victoria 3 patch (e.g. 1.12.4 → 1.13). Follow in order — earlier steps unlock later ones.

## 0. Prerequisites

- Local clone of vanilla at `~/src/vic3` (full git history; the prior version is in git history). Set `vanilla_source_repo_path` in `paths.local.json` to it (`setup.py` accepts any existing directory there, so double-check it isn't pointing at a digest folder). **On a fresh machine without the clone, get it before starting** — the engine-surface diff works from digests alone (§ 3), but GUI merges (§ 5), `REPLACE:` re-bases and the `/validate/*?old_ref=` endpoints all need the exact prior-version files, and Steam's rollback branch is usually the *latest* prior hotfix, not the version the mod was last migrated on.
- [Modding-Digests](https://github.com/Victoria-3-Modding-Co-op/Modding-Digests/) clone at `vic3_modding_digests_path` (`~/src/Modding-Digests` by default). The mod state server auto-pulls this on cold start; if absent, run `.venv/bin/python mod_state_server.py` once and it'll clone. The digests short-circuit much of § 3.
- Mod state server runnable: `python3 mod_state_server.py` (use `python3`, not `python`, on this system).
- The mod loads cleanly on the prior vanilla (i.e. before starting the migration, the mod is in a known-good state).
- **Engine-doc baseline:** as of vanilla 1.13.5 the `~/src/vic3/docs/` directory of engine-doc log dumps no longer ships with vanilla — upstream moved them to Modding-Digests. `mod_state_server` resolves the highest-version digest checkout automatically (see `_engine_docs_source()` in `mod_state_server.py`), so `vanilla_snapshot_docs_path` in `paths.local.json` is now optional. Leave it unset to use the digest version, or point it at a hand-maintained local snapshot if you regenerate engine docs via in-game `script_docs`.

## 1. Snapshot the current mod (BEFORE applying patch)

```bash
python3 scripts/snapshot_balance.py            # writes docs/data/balance_snapshot.json via --out default
git add docs/data/balance_snapshot.json
git commit -m "snapshot mod balance before <vanilla-version> migration"
```

Captures key gameplay values (combat units, ship types, late-era tech modifiers, law modifiers) so you can verify the *intent* survives any rebalancing later. Without this, post-patch rebalancing requires recall ("what were the pre-patch hypersonic platform stats again?").

> **Footgun:** the script writes to `--out` (default `docs/data/balance_snapshot.json`) — it does **not** print JSON to stdout. `python3 scripts/snapshot_balance.py > somefile.json` silently writes the snapshot to the *default committed path* and leaves `somefile.json` empty, clobbering the pre-migration baseline. To diff current-vs-baseline after a rebalance, pass an explicit temp path: `python3 scripts/snapshot_balance.py --out /tmp/new.json` and diff against `git show HEAD:docs/data/balance_snapshot.json` (or `git checkout -- docs/data/balance_snapshot.json` to restore if you clobbered it). Note the snapshot's `ship_types` block tracks `modification_construction_cost`/crit/blockade/damage but **not** `goods_input_steel_add` and does not cover `ship_modifications` (gun mods) at all — cross-check those via `git diff`.

## 2. Identify the diff baselines

In `~/src/vic3`:

```bash
git -C ~/src/vic3 log --oneline | head -20
```

Find the commit that bumped to the new version (e.g. "v1.13"). Its parent is the prior version baseline. Save these as `OLD_REF` and `NEW_REF`. (The clone lives wherever `vanilla_source_repo_path` points — `~/vic3` on some machines.)

**If the clone doesn't have the new version yet**, commit it from the live install. The clone `.gitignore`s large binaries, so mirror those excludes and let `--delete` capture vanilla's removals:

```bash
rsync -r --delete --exclude='*.mp3' --exclude='*.dds' --exclude='*.bank' --exclude='*.bk2' --exclude='*.flac' \
      --exclude='*.mehs' --exclude='*.otf' --exclude='*.tga' --exclude='*.png' \
      "<base_game_path>/game/" <clone>/game/
git -C <clone> add -A game && git -C <clone> diff --cached -M --shortstat   # expect many R100 renames, not churn
git -C <clone> commit -m "<version> (<codename>)"                          # local only; restart mod_state_server
```

Check `git diff --cached --ignore-cr-at-eol --shortstat` matches the plain one (no line-ending churn) before committing.

**Vanilla renames files, not just identifiers.** 1.14 renamed 224 files (laws `00_*` → `01_`/`02_*`, per-language loc). That silently breaks two things: a mod file overriding vanilla *by same path* stops overriding and starts duplicating keys, and any at-risk list built from the new patch's file names misses targets whose old file had a different name. Check both against the real rename list:

```bash
git -C <clone> diff -M --name-status OLD_REF NEW_REF | awk '$1 ~ /^(R|D)/ {print $2}' | sed 's#^game/##' \
  | while read p; do [ -e "$p" ] && echo "same-path override of renamed/deleted vanilla file: $p"; done
```

## 3. Engine-doc diff

**Start here:** open `<vic3_modding_digests_path>/<NEW_VERSION>/changes_breaking.md` and `changes_script_docs.md` (e.g. `~/src/Modding-Digests/1.13.0/`). They contain pre-computed Removed/Added/Renamed lists for scopes, effects, triggers, event targets, iterators, on-actions, plus narrative breaking-change writeups for each major mechanic. The categories below map onto the digest's section headings — let them do the heavy lifting first.

Fall back to manually diffing `OLD_REF`/`NEW_REF` in `~/src/vic3` only when:
- The new vanilla version doesn't yet have a digest (typical for early hotfixes — check `~/src/Modding-Digests` after `mod_state_server` startup, since it's auto-pulled).
- You need a class of identifier the digest doesn't enumerate (e.g. script-value renames, modifier-type-definition shape changes).
- A digest entry needs verification against the actual log file (`<vanilla_snapshot_docs_path>/<modifiers|effects|triggers|on_actions>.log`).

Manual-diff workflow when needed: compare `docs/modifiers.log`, `docs/effects.log`, `docs/triggers.log`, `docs/on_actions.log` between `OLD_REF` and `NEW_REF` in vanilla. Categorize:

- **Removed**: identifiers that existed in OLD but not NEW. These break the mod hardest. Examples from 1.13: `country_convoys_capacity_*`, `unit_navy_*`, `unit_blockade_*`, `state_building_naval_base_max_level_add`, `military_formation_movement_speed_mult`, `is_ruler`/`is_heir` triggers, `country_max_declared_interests_*`.
- **Renamed**: re-named pairs (e.g. `has_role` → `has_role_of_type`). Identify by name similarity.
- **Semantics changed**: same name, different meaning. Watch for `relative_*` triggers and similar.
- **Added**: useful new modifiers/effects/triggers the mod might want to leverage.

**Diff the cumulative span, not just the newest digest.** The baseline is the mod's last migrated version (`.metadata/metadata.json` → `supported_game_version`), which may sit several hotfixes back — 1.13.9 → 1.14.2 crossed 1.13.10 and 1.13.11, and 1.13.10 alone touched 10 of the mod's GUI overrides. Concatenate every intervening digest's `changes_files.md` when enumerating at-risk files.

**No vanilla clone needed for the engine surface.** Every digest ships the full `docs/*.log` dump, so diff the two endpoints directly (run under `bash`):

```bash
cd <vic3_modding_digests_path>
hdr() { grep -oE '^##+ [A-Za-z0-9_:|{}\\]+' "$1" | sed -E 's/^#+ //' | sort -u; }
for k in effects triggers event_targets; do echo "== $k"; comm -3 <(hdr OLD/docs/$k.log) <(hdr NEW/docs/$k.log); done
echo "== modifiers"; comm -3 <(grep -oE '^[A-Za-z0-9_]+:$' OLD/docs/modifiers.log | sort -u) <(grep -oE '^[A-Za-z0-9_]+:$' NEW/docs/modifiers.log | sort -u)
```

Then grep **all** of `common/ events/ gui/ localization/` for every removed name — `effect_trigger_validity_audit` covers the 16 directories in its `SCAN_ROOTS` (events, the scripted helpers, on-actions, and the script-bearing `common/` entity dirs: laws, journal entries, diplomatic actions/plays, treaty articles, decisions, scripted buttons/progress bars, political movements, power-bloc principles, character interactions, script values), but `gui/`, `localization/` and any `common/` dir outside that list are still only reachable by grep. Everything inside `SCAN_ROOTS` flags on the next `POST /reload` instead (1.14's `has_war_exhaustion` in `nuke.txt` is the case that motivated #295). After re-bootstrapping the catalog (§ 4), `git diff docs/engine/effect_trigger_valid_keys.txt | grep '^-'` also lists removed *vanilla script values* — grep the mod for those too. GUI 3-way merges, `REPLACE:` re-bases and loc-drift checks still need the vanilla clone (§ 5).

The shell helpers in `<vic3_modding_digests_path>/script/` (`diff-modifiers.sh`, `diff-documentation.sh`) are the same ones the upstream uses to generate the digests — handy when running against a vanilla version not yet covered.

**Modifier-type-definitions name diff** — catches registrations added/removed even when no digest exists yet (vanilla `.txt` files there are BOM-prefixed and unindented, so plain `grep "^\w+ = {"` misses everything):

```bash
extract() { cat "$1"/*.txt | sed 's/^\xEF\xBB\xBF//' | grep -oE '^[a-z0-9_]+[ \t]*=[ \t]*\{' | sed 's/[ \t={]*$//' | sort -u; }
extract ~/src/vic3/game/common/modifier_type_definitions            > /tmp/mt_old.txt   # at OLD_REF checkout
extract "<base_game_path>/game/common/modifier_type_definitions"    > /tmp/mt_new.txt   # live install
comm -13 /tmp/mt_old.txt /tmp/mt_new.txt   # added in new patch
comm -23 /tmp/mt_old.txt /tmp/mt_new.txt   # removed → grep the mod for every one of these
```

This found both 1.13.9 breakage classes (the law-enactment rename and the harvest-condition deregistration) before the game was ever launched.

You can use the mod-state server validator as a gating signal: after preliminary edits, `curl http://localhost:8950/validate/engine-coverage` returns the modifier names the mod uses that are no longer recognized.

### Known vanilla renames (cumulative across patches)

When `debug.log` shows `Unexpected token: <name>` or `inject/replace to a non-existing entry: <name>`, check this table before grepping vanilla. Each entry is a vanilla rename the mod has been bitten by. Add new ones as you find them.

| Old name | New name | Where it bites | Notes |
|---|---|---|---|
| `should_be_pinned_by_default` | `should_be_pinned_by_default_uninvolved_or_context` | Journal entry top-level field | Renamed sometime around 1.13. Symptom: `Unexpected token: should_be_pinned_by_default` in debug.log. Bulk rename: `for f in $(grep -rl "should_be_pinned_by_default[^_]" common/journal_entries/); do sed -i 's/should_be_pinned_by_default\([^_]\)/should_be_pinned_by_default_uninvolved_or_context\1/g' "$f"; done` |
| `telecommunications` (tech) | `telephone` (tech) | `INJECT:` targets in `common/technology/technologies/modified.txt` | Vanilla split the old umbrella tech. The intelligence-capacity slot the mod wanted lives on `telephone`. |
| `canning` (tech) | `canneries` (tech) | `INJECT:` targets in `common/technology/technologies/modified.txt` | `vacuum_canning` still exists; only the early-era `canning` was renamed. |
| `has_role` (trigger) | `has_role_of_type` (trigger) | All character-role checks | Bulk-replaceable. |
| `country_law_enactment_time_mult` | `country_law_enactment_speed_mult` | Static modifiers, law `modifier` blocks | 1.13.9 rework. **Semantics flip with the rename**: time-mult (negative = faster) → speed-mult (positive = faster). Vanilla's convention was sign-flip at the same magnitude. The six per-law variants renamed identically (`country_enactment_time_law_X_mult` → `country_enactment_speed_law_X_mult`). A `LAW_ENACTMENT_MIN_SPEED_FACTOR` define floors stacked maluses. |
| `country_war_exhaustion_casualties_mult` | `country_war_support_casualties_mult` | Laws, principles, traits, amendments, static modifiers | 1.14 war support rework. **Same sign** (both `color=bad`; vanilla multiplies the casualty loss by `1 + mult`, floored at 0). 1.14 also added `country_war_support_battles_{increase,decrease}_mult`. |
| `has_war_exhaustion` (trigger) | `has_war_support` (level) — **not** `has_war_support_change` | "War is going badly" AI/event checks | 1.14. War support is now 0–100 (low = bad), so `exhaustion > X` becomes `has_war_support value < Y`; prefer `define:NDiplomacy\|WAR_SUPPORT_RADICALIZATION_THRESHOLD` / `WAR_SUPPORT_DRIFT_TARGET` over literals. `has_war_support_change` is the signed per-beat delta (vanilla uses `< -5`). |
| `add_war_exhaustion` / `additional_war_exhaustion` / `war_exhaustion_from_acceptance_of_dead` | `add_war_support_change` / `additional_war_support_change` / `war_support_from_acceptance_of_dead` | Events, script values | 1.14. **Sign flips**: positive exhaustion was bad, positive war support change is good. `enemy_contested_wargoals` has no direct successor (see `has_stalled_wargoal_against` / `enemy_side_occupation`). |
| `has_war_support` / `add_war_war_support` / `add_diplomatic_play_war_support` (**same names, new scale**) | — | Hand-written war support checks and deltas | 1.14 moved war support from −100..100 to 0..100 without renaming anything, so nothing errors. Vanilla halved all its deltas (100→50, 10→5, −10→−5); map levels as `(v+100)/2`. 1.14 migration: nuke aftermath guard `> -65` → `> 17.5`, −25 → −12.5; `state_war_support_monthly_add` and `country_war_support_monthly_add_religion` sources halved. Grep for literals: `git grep -nE "has_war_support\|add_war_war_support\|add_diplomatic_play_war_support" -- common events`. |
| `concept_war_exhaustion` (loc concept) | `concept_war_support` | `[concept_war_exhaustion]` in loc strings | 1.14. A dead concept link renders broken with no log line — `concept_reference_audit` / grep. |

**Deregistration without removal** (same silent-no-op symptom, different fix): a patch can remove a `modifier_type_definitions` registration while keeping the underlying entity type. 1.13.9 deregistered `state_harvest_condition_{hailstorm,torrential_rains}_{impact,duration}_mult` although both harvest conditions still exist — any mod use silently no-ops. Fix by re-registering the type in the mod's `common/modifier_type_definitions/` (copy the last-known vanilla registration shape from `~/src/vic3` git history), not by deleting the mod's uses. Detect via the modifier-type-definitions name diff (BOM-aware extraction, see below), which catches what `debug.log` never reports.

### Symptoms-to-cause cheat sheet

- `Unknown modifier type: X` (debug.log, `script_parse_error`) → either a vanilla rename (check table above) or a missing dynamic-modifier-type registration in `common/modifier_type_definitions/`. Vanilla only auto-registers SOME axis combos for ship_battle / ship_construction / goods_input/output patterns — modded ships, modded goods, AND vanilla ship/good types the mod uses on a NEW axis all need explicit registration. See `docs/guides/scripting_best_practices.md` § "Dynamic Modifier Type Definitions".
- `Unexpected token: X` → renamed top-level field (table above) or invalid syntax. JE pinning fields and law fields tend to drift across patches.
- `Unknown trigger type: X` → renamed/removed trigger or event-target. Validate via `curl 'http://localhost:8950/engine-docs/triggers?q='` and `…/engine-docs/event-targets?q=`.
- `Duplicated key X will not be created` → mod redeclared a top-level entity vanilla owns. Switch to `INJECT:X = { ... }` (see `docs/guides/scripting_best_practices.md` § "Top-Level Database Collisions").
- `inject/replace to a non-existing entry: X` → vanilla renamed or removed `X`. Use the table or the symptoms-to-cause grep workflow.
- `Value of wrong type in '<file>:<line>'. Got value of type 'none'` → script value or trigger reading an uninitialized `global_var:` / `variable:`. Initialize from `on_game_started` (see `docs/guides/scripting_best_practices.md` § "Global Variable Initialization Timing").

## 4. Re-run all auto-generators

The auto-generators read vanilla and emit mod files. Re-running them after a vanilla patch picks up vanilla's content changes for free. Run in this order:

```bash
python3 apply_ideologies.py                          # common/ideologies/modified.txt
python3 ig_feminism.py                               # common/interest_groups/00_*.txt (8 files)
python3 pop_needs_curves.py                          # common/buy_packages/00_buy_packages.txt
python3 resources.py                                 # map_data/state_regions/*.txt
python3 scripts/generators/gen_formable_regions.py   # common/geographic_regions/te_formable_regions_generated.txt
python3 effect_trigger_validity_audit.py bootstrap   # docs/engine/effect_trigger_valid_keys.txt (frozen valid effect/trigger catalog)
python3 scripts/generators/fold_vanilla_loc_accessors.py  # localization_accessor_vanilla_extras.py (1.14 added 117 accessors; 1.14.3 a further 5 — point releases count)
```

**Run `fold_vanilla_loc_accessors.py --dry-run` first, and look each new accessor up in vanilla loc before folding.** The generator folds every flagged accessor as `"value"`, which is right for a terminal atom and wrong for a *type-changing* one — and folding the latter still makes the flag go away, by making the audit stop checking the rest of the chain. That is a silent loss of engine-surface knowledge, not a fix. 1.14.3's `State.GetStateInfamyPerspective` is the worked example: it returns a **country** (`"[State.GetStateInfamyPerspective.GetNameNoFormatting] already owns [State.GetName]"`), so it goes into `_BUILTIN_ACCESSORS_BY_TYPE` by hand *before* the fold. The tell is a flagged chain with another step after the flagged accessor.

Re-bootstrap the effect/trigger catalog **after** the engine-doc summaries (`effects_summary.txt` / `triggers_summary.txt`) are refreshed in step 3, since it unions those names with vanilla's effect-corpus keywords. A stale catalog produces false positives (new vanilla effects flagged as unknown).

If the vanilla map changed (states removed/renamed/split), edit `deposits_config.json` to point old keys at successors **before** running `resources.py`. See `docs/auto_generated_files.md` for the full ownership table.

`gen_formable_regions.py` reads vanilla `common/strategic_regions/*.txt` and re-expands the four EU/Africa/N.America/Earth formable regions to explicit state lists — re-run if vanilla rebalances strategic regions or renames states. The script also fails loudly if a configured strategic region disappears, which is the signal to update its inline config.

## 5. GUI override re-merge

**Enumerate the at-risk set deterministically.** Don't rely on agent inference or memory of "which files changed" — vanilla often touches GUIs that look incidental. Use:

```bash
# Run from the repo root (mod_path). VAN is the vanilla git clone —
# path_constants.vanilla_source_repo_path (VIC3_VANILLA_REPO), not a hardcoded path.
VAN=$(python3 -c 'import path_constants; print(path_constants.vanilla_source_repo_path)')
find gui -name "*.gui" -type f | while read rel; do
  vfile="$VAN/game/$rel"
  if [ -f "$vfile" ]; then
    changed=$(git -C "$VAN" log --oneline OLD_REF..NEW_REF -- "game/$rel" | head -1)
    if [ -n "$changed" ]; then
      echo "AT-RISK: $rel  [$changed]"
    fi
  fi
done
```

In the 1.13.5 migration, an exploration agent reported 2 at-risk GUI files; the shell loop above found 5. The missed three included `military_formation_panel.gui`, whose unrebased override silently broke the move-formation button because vanilla renamed `ToggleArmyMovement` → `ToggleArmyAdditionalActions` and `MOVE_MILITARY_FORMATION` → `ADDITIONAL_ACTIONS_MILITARY_FORMATION` in the onclick handler.

For each at-risk file, run a 3-way merge with vanilla's pre- and post-patch versions. See `docs/guides/gui_modding_guide.md` § "GUI 3-way merge across vanilla patches" for the exact `git merge-file` command. In the 1.13 migration this resolved 14 of 17 GUI overrides cleanly with 5 manual conflicts.

**Prove each merge preserved the mod's delta.** Strip BOM/CR from all three inputs, merge, then compare the set of non-blank changed lines of `diff(OLD, mod)` against `diff(NEW, merged)` — they must be identical (0 lost, 0 extra). This catches both a mod edit the merge dropped and a stale pre-patch vanilla line the merge kept. In 1.14 all 11 merges passed; the only 2 conflicts were mod-side trailing whitespace. Restore each file's BOM when copying back.

**Sweep every `REPLACE:`/`INJECT:` target, not just the ones in changed files.** Locate each target key in the full `OLD_REF` and `NEW_REF` trees of its `common/` subfolder (rename-proof) and diff the block. A changed `REPLACE:` target needs vanilla's delta ported; a changed `INJECT:` target is usually fine (the mod appends sibling `modifier` blocks and vanilla's additions stack with them), but read the diff. 1.14: 898 targets, 0 removed, 6 changed — `ideology_pacifist` (generator-owned) plus war-support lines added inside 5 injected laws/techs.

**A conflict-free merge is not a clean merge.** `git merge-file` happily produces a 0-conflict result when vanilla's edits don't textually overlap the mod's edits — but vanilla may have renamed a function the mod's untouched code-path still calls. After every merge, grep the merged file for any identifier vanilla deleted/renamed during this patch (use the engine-surface delta from step 3). The engine doesn't log GUI script errors, so a broken onclick handler manifests as a silently unresponsive button, not a `debug.log` entry — there's no runtime safety net.

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

## 6b. Vanilla constants the mod mirrors (silent-drift check)

A separate class from step 6's breakages: values the mod **copies or cancels** rather than references. Vanilla changing one produces **no error, no log line and no validator finding** — the mod keeps loading and quietly computes the wrong number. Re-read each row against the new vanilla on every bump.

All of these come from the monetary-policy system (`docs/systems/mod_systems.md` § Banking Cycle → **Monetary Policy (phase 1)**; spec `docs/systems/monetary_policy_design.md` §7, §16.1). It computes the government's borrowing rate itself, so it cancels vanilla's own interest sources — each on the entity that grants it — and re-expresses them on its two premium types.

| Vanilla (under `$BG/game/`) | Value the mod assumes | Mod side | If vanilla changes it |
|---|---|---|---|
| `common/static_modifiers/00_code_static_modifiers.txt:12` — `base_values` | `country_loan_interest_rate_add = 0.2` | `country_loan_interest_rate_add = -0.2` inside the mod's own `INJECT:base_values` block in `common/static_modifiers/extra_modifiers.txt` | the cancel stops zeroing the flat base rate; **every** country's rate paid is off by the difference |
| `common/country_ranks/00_country_ranks.txt` — six `country_loan_interest_rate_mult` (`great_power` −0.5 :44, `major_power` −0.25 :82, `insignificant_power` +0.25 :140, `unrecognized_major_power` +0.5 :175, `unrecognized_regional_power` +0.75 :210, `unrecognized_power` +1.0 :242; `minor_power` and `decentralized_power` carry none) | each cancelled with its exact inverse | `common/country_ranks/te_monetary_rank_injections.txt` | a changed value leaves a residual multiplier on the *whole* stack for that rank; a **new** rank mult is not cancelled at all |
| `common/laws/01_economic_system.txt:477` — `law_laissez_faire` | `country_loan_interest_rate_mult = -0.25` | `common/laws/te_monetary_law_injections.txt` (+0.25 cancel, −0.5pp premium) | same residual-multiplier failure, on one law |
| `common/technology/technologies/30_society.txt` — five finance techs at `country_loan_interest_rate_add = -0.02` (`banking` :209, `central_banking` :599, `mutual_funds` :1226, `international_exchange_standards` :1473, `modern_financial_instruments` :1647) | each cancelled with its exact inverse, `+0.02` | `common/technology/technologies/te_monetary_tech_injections.txt` | a changed value leaves a residual flat `_add` on every country holding that tech; a **sixth** finance tech is not cancelled at all, and a dropped one leaves the mod adding 2pp. Watch `country_minting_mult = 0.1`, which shares the vanilla `modifier = { }` block: it is the in-game tell that the INJECT is summing rather than overwriting |
| `common/modifier_type_definitions/00_modifier_types.txt:662-669` — the `country_loan_interest_rate_add` **type definition** (`decimals=0 color=bad percent=yes game_data={ai_value=0}`) | every field but `decimals` copied verbatim | `REPLACE:country_loan_interest_rate_add` in `common/modifier_type_definitions/banking_cycle_modifier_types.txt`, at `decimals = 1` | a `REPLACE` restates the whole definition, so any field vanilla adds or retunes is silently dropped by the mod's copy |

```bash
BG="$(python3 -c 'import path_constants; print(path_constants.base_game_path)')/game"
grep -n country_loan_interest_rate_add "$BG/common/static_modifiers/00_code_static_modifiers.txt"
grep -n country_loan_interest_rate_mult "$BG/common/country_ranks/00_country_ranks.txt" "$BG/common/laws/01_economic_system.txt"
grep -rn country_loan_interest_rate_add "$BG/common/technology/technologies/"
grep -n -A8 '^country_loan_interest_rate_add=' "$BG/common/modifier_type_definitions/00_modifier_types.txt"
```

The three INJECT files carry the same warning in their own headers, so a fix made here should be echoed there (and vice versa). All three cancels rest on INJECT blocks summing with vanilla's, which is confirmed in game for every shape the mod uses (ranks and techs 2026-09-19, laws and flat keys 2026-09-20); see `scripting_best_practices.md` § INJECT.

## 7. Special-case: combat units / ship types

Patches sometimes add new entity TYPES (1.13 added `ship_types/`, replacing the old `combat_unit_types` naval section). The migration is not a rename — it's a system replacement. Strip the old entries first to make the mod load, then port the entries to the new framework as a follow-up.

If the mod has late-era ships beyond vanilla's tier (the case here: nuclear submarine, hypersonic platform, etc.), preserve their progression curve from the snapshot in step 1. Pre-1.13 mod's progression was roughly 2-3× per era (battleship 100 → fleet carrier 300 → nuclear supercarrier 700 → arsenal ship 1800 → hypersonic 4000). Match this scaling against vanilla's new top-tier baseline (super_dreadnought).

**1.13.9 naval anchoring (issue #223, the second wave after 1.13.7's #160–#164).** Established, for future migrations: (1) **Crit** — mod ships map to their vanilla *class analog*, not a mod-flavored band, because 1.13.9 made crits ignore 100% of armor (`NAVAL_BATTLE_CRIT_ARMOR_REDUCTION = 1.0`) and cut crit multipliers ~8× in compensation. Ship-base `ship_critical_hit_multiplier_add` sits at vanilla's 0.25 (capital/cruiser) / 0.50 (sub/destroyer/carrier) / 0.10 (troop); ship-base `ship_critical_hit_chance_add` at vanilla's 0.05/0.10/0.15/0.05. Gun-mod crit tiers (0.1/0.15/0.2) already match vanilla — leave them. (2) **Gun damage band** — vanilla symmetrized to ≈±45% about the *medium* base module (not the ±25% the wiki implied); mod gun tiers use light = med×0.55, high = med×1.45, medium unchanged. (3) **Capital cost** — vanilla doubled the dreadnought family selectively (cruisers/carriers scaled less), so scale only `ship_group = capital_ships` mod ships; top tier lands ~3× the new super_dreadnought. (4) **Construction speed** — the flat `ship_construction_progress_max_add = 25` matches vanilla's *unchanged* base; capital-group mod ships auto-inherit the new `country_ship_group_capital_ships_construction_progress_max_add` from `arc_welding`/`concrete_dockyards`, so no per-ship change is needed. (5) **Blockade** — #163's strength:resistance ratio anchor still holds; verify, don't transplant.

## 8. Triage runtime errors

Load the game with the migrated mod, run an observer game for a decade or so, then triage the error log:

```bash
curl -s http://localhost:8950/logs/error?dedupe=true | python3 -m json.tool
```

For each entry:

1. Locate file and line.
2. If the file is a vanilla path that doesn't exist in mod, it's a vanilla bug. Cross-reference `docs/vanilla/vanilla_known_bugs.md` and add new entries as discovered.
3. If the file is mod-owned (or mod-auto-generated), trace the source.

## 8b. Refresh `docs/vanilla/vanilla_economy_reference.md`

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

(See `docs/guides/python_tools.md` for the filter; in absence of the filter, manually classify the 29-or-so unknown entries against `common/modifier_type_definitions/`.)

The bar is **0 vanilla breakages**. Mod-defined custom modifier types (`country_sr_*`, `country_covert_*`, `cultural_hegemony_*`, etc.) reported as "unknown" by the validator are pre-existing limitations of the validator, not real breakages. **But don't extend that to unregistered per-entity dynamic types**: the 7 `state_custom_religion_*_standard_of_living_add` unknowns in the 1.14 migration were dismissed as a validator limitation and were real no-ops (the engine generates those types only for vanilla religions). Confirm any unknown that is *not* a mod-registered custom type against debug.log's `Unknown modifier type` before waving it through.

## 9b. Deploying for the in-game check

`./scripts/deploy.sh` dry-runs first — read its summary before `--apply`. The deploy target lives in (OneDrive-synced) Documents and may have been deployed from another machine or an older checkout; a large dry-run delta or `deleting` lines for files the repo dropped long ago means you'd be overwriting state you haven't looked at.

## 10. Verify in-game

- Game loads to main menu without `error.log` spam.
- 1836 starts smoke-test (Britain, France, Japan, one minor): no error spam in first month, all major mod systems' JEs appear.
- Late-era starts smoke-test (1936 if start dates allow): mod's modern naval ships build, fight, upgrade.
- Open every overridden GUI panel and confirm layout is sane.
- Run validator one last time after a few minutes of in-game activity.
