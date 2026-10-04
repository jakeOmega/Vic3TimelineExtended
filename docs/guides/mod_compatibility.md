# Compatibility with Other Mods

How two Victoria 3 mods collide, how to check another mod against this one, and the compatibility work done so far (Realism Ai Historical Flavor Mod). Issue #557 covers the Community Mod Framework.

## How two mods collide

- **Same relative path:** the copy from the mod later in the playset replaces the whole file. This holds for every folder, and it is the only way to change `map_data/state_regions/` or a `.gui` file. State regions don't take `INJECT`/`REPLACE` (they aren't on the 1.12 `inject_types` list in Modding-Digests). GUI files don't either.
- **Same top-level key, no directive:** the engine logs `Duplicated key X will not be created` and keeps one copy (`scripting_best_practices.md` § "Top-Level Database Collisions"). Fix it with a key you own. Script values are the exception: the later definition replaces the earlier one.
- **Directives:** `INJECT:` blocks sum with the entry, flat keys and nested blocks alike. `REPLACE:` / `REPLACE_OR_CREATE:` throw away everything before them, so a `REPLACE` that applies after another mod's `INJECT` silently removes it. Directives are *assumed* to apply in file-name order across vanilla and every mod (#557; never tested). That is why `modified.txt` beats a `dsk_*.txt` but loses to a `usfp_*.txt`. A compatibility patch should not depend on that order: it `REPLACE`s with a fully merged body from a `zzz_` file and loads last.
- **On-actions merge** their `on_actions` / `events` lists across files. An `effect =` block on a vanilla on-action replaces vanilla's own effect. This mod never adds one (`scripting_best_practices.md`); other mods do, and it costs us nothing because we only use the list forms.
- **Defines** merge key by key. **Loc:** a key defined in two files takes the text of the file that sorts last by name, across mods (`CLAUDE.md`). **Named colours** merge per colour name.
- **GUI types defined in two files:** which one wins is untested (#557).

## Checking a mod

1. List same-path files in `common/ events/ gui/ localization/ map_data/` and diff each side against vanilla. Diff against the vanilla version the other mod was built for as well (`~/src/vic3` holds 1.13.9). That separates its deliberate changes from version drift and shows whether its copies of vanilla files would undo a newer patch.
2. For each `common/` folder, list top-level keys both mods define, with the directive and file on each side. INJECT on both sides is safe; anything involving a `REPLACE` or a plain key is a conflict.
3. Compare defines key by key, GUI `type`/`template` names, event namespaces and ids, and English loc keys (noting which side's file sorts last).
4. Look at what the other mod adds that our per-entity injections never reach: a new country rank, laws added to vanilla law groups, `effect =` blocks on vanilla on-actions.

`scan_unhandled()` in `scripts/generators/build_realism_ai_compatch.py` covers steps 1–3 and can be pointed at another mod.

**Fix natively** when one of our own generic keys collides: rename it to one we own. **Use a patch mod** when the fix needs the other mod's content, such as merged files or its own values.

## Realism Ai Historical Flavor Mod

Workshop `2893069455`, mod id `realism_ai_historical_flavor_mod`. Checked against version 10.9 on 2026-10-04 with Timeline Extended 1.1.7 and the 1.14.5 game. It bundles many flavour mods, plus the Community Mod Framework's event windows and text icons. Its metadata says `1.13.*`, but every vanilla file it ships a copy of is unchanged between 1.13.9 and 1.14.5, except one portrait DNA file. So its copies don't undo any 1.14 change. Its copies of `acw_je_events.txt`, `native_resettlement.txt` and `russo_chinese_events.txt` drop one event each, and this mod references none of them. Nothing here has been tested in game.

### Conflicts

| Overlap | Without the patch | Fix |
|---|---|---|
| 15 `map_data/state_regions/` files (all but `06_central_america` and `99_seas`) | Whichever mod loads later wins each file. RA later: our deposits for the 14 mine types and the state traits we add in 21 states are gone. Ours later: RA's arable land and capped resources, rescaled in about 600 states, are gone. | Patch: RA's files with our deposits and traits applied by `resources.py` |
| `gui/topbar.gui` | RA later: no Banking phase in the top bar. Ours later: RA's second row (prestige, infamy, legitimacy, innovation, flotillas, battalions) is gone. | Patch: RA's file, widened to our 765 with our Banking widget after MONEY |
| 16 vanilla ideologies (RA `REPLACE_OR_CREATE`, ours `REPLACE`, `INJECT` for Egalitarian) | Our `modified.txt` sorts after RA's `dsk_ideologies_replace_yuanban.txt`, so for 15 of them RA's stances on the laws it adds to vanilla groups (Japanese press laws, police, revolutionary armies) are dropped and read as neutral. RA's `usfp_leader_ideologies.txt` sorts after ours, so on Jacksonian Democrat our governance-principles, distribution-of-power and bureaucracy stances are dropped. | Patch: `REPLACE` with RA's body plus our `ideology_modifications.py` edits |
| `law_ethnostate`, `law_national_supremacy` | Our `REPLACE` removes RA's earlier `TRY_INJECT` of authority, legitimacy, birth-rate and conscription modifiers. | Patch: `REPLACE` with our body and RA's modifiers summed in |
| RA's `super_power` rank (above Great Power) | None of our per-rank injections reach it: cultural pull, covert slots, intelligence capacity, the credit-standing premium, and the cancel of the rank's loan-interest discount. | Patch: `INJECT:super_power` with our Great Power values; the interest cancel matches RA's −55% |
| `dp_leadership_india` (both define it as a plain key) | One copy is dropped. If RA's survives, Bharat's leadership play is gated on Pan-Nationalism instead of Decolonization. | Native: ours renamed `dp_leadership_bharat` |

### Checked, not conflicting

- `INJECT` on both sides, touching different fields: `ai_strategy_default`, the great, major and minor power ranks, 17 `pmg_*` groups, `pm_industrial_port`, `pm_modern_port`, `pm_steam_trawlers`, `law_total_separation`.
- 21 vanilla on-actions both mods hook. RA's `effect =` blocks on `on_diplo_play_back_down`, `on_monthly_pulse`, `on_monthly_pulse_country` and `on_war_end` replace vanilla's effect, not ours.
- Defines (no key in common), named colours, events, scripted effects, triggers and values, journal entries, buildings, decisions, game rules, static modifiers, modifier types, and GUI types other than the top bar's.
- Loc: only `dp_leadership_china*`, which is an orphan in RA's `dsk_l_english.yml`; our file sorts later, so our text shows.
- RA's `eventwindow.gui` is CMF's superset of vanilla's, and none of our events set `gui_window`.
- RA doesn't bundle the CMF files #557 is about (`com_gui_journal_entry.gui`, the `00_MPM_*` GUI files, the law `REPLACE_OR_CREATE`s). Those collisions apply only when a player also enables CMF itself.

### Left as they are

- RA's new laws have no stance in this mod's own ideologies. They read as neutral, and our law-consistency sweep doesn't know them.
- Our resource and economy tuning assumes vanilla's map amounts, and RA rescales them.
- RA's `NAI` defines change AI spending and construction.

### The patch

`scripts/generators/build_realism_ai_compatch.py` builds it into `build/compat/realism_ai/` (gitignored). `--deploy` copies it into the game's mod folder as `Vic3TimelineExtended_RealismAI_Compat`. `--check` exits 1 when that copy is stale. Each part checks its own output and the build stops when an anchor is missing or a merge didn't take. The closing rescan lists overlaps the patch doesn't handle (`--strict` makes them fatal). The rescan is how an RA update shows up.

- **Load order:** Realism AI, then Vic3TimelineExtended, then the patch.
- **Rebuild** after an RA update, and after changing `ideology_modifications.py`, `common/laws/modified.txt`, `deposits_config.json`, `state_trait_config.json`, `gui/topbar.gui`, or `common/country_ranks/`.
- **Publishing** it ships RA's own files (merged), which needs the RA author's permission. Its metadata declares RA as a dependency. It can't declare Timeline Extended, whose `metadata.json` has an empty `id`.

### In-game checks

1. `debug.log`: no `Duplicated key` for `dp_leadership_*`, and no errors from `zzz_te_realism_ai_*` or the patched `topbar.gui`. Set aside RA's own errors.
2. California: RA's capped resources and our deposits are both there (both mods edit its resources).
3. Liberal's ideology tooltip lists Free Speech once, with RA's laws in it; Jacksonian Democrat shows our bureaucracy stances.
4. Ethnostate's modifier breakdown shows +400 authority (ours 200 plus RA's 200) and RA's birth-rate line.
5. The top bar shows RA's second row and the Banking phase after MONEY, and the alerts don't overlap it.
6. A super power's credit standing and loan interest match a great power's.
