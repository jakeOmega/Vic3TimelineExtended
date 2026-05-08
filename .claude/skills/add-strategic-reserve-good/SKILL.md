---
name: add-strategic-reserve-good
description: Add one or more new goods to the Strategic Reserve journal entry in the Vic3TimelineExtended mod (the JE that lets a country stockpile strategic goods in a Hub building). Use whenever the user mentions extending, adding to, or putting a new good into the Strategic Reserve / SR system / `je_strategic_reserve` — phrases like "add gold to the reserve", "extend SR to cover steel", "add a new strategic reserve good", "let players stockpile X". Also triggers when the user wants to change which goods the SR Hub buys/sells or adds new per-good progress bars to that journal. Touches ~10 files in a strict per-good pattern; this skill walks through every one and surfaces the vanilla mult-axis registration gap that silently breaks new goods otherwise.
---

# Add a strategic-reserve good

## When to use

The Strategic Reserve is a country-scoped stockpile system anchored on `je_strategic_reserve` and the `building_strategic_reserve_hub` building. Each covered good has its own stored stockpile, configurable weekly storage/withdraw rate, decay rate, fill bar, and pair of +/- buttons in the JE. The system already covers `grain`, `ammunition`, `oil`, `small_arms`, `artillery`, `aeroplanes`, `tanks`. Adding any new good touches ~10 files with a strict copy-paste-modify pattern — miss one and the good silently does nothing in-game.

This skill is a workflow, not a script. The repetition is mechanical, but the decisions per good (tech gate, decay rate, mult-axis check) need judgment. Drive it file-by-file; the verification step at the end is non-optional.

## Decisions to make first (ask the user, don't guess)

For each good the user wants to add, lock these decisions before touching any file. Use `AskUserQuestion` if any are ambiguous.

1. **Good ID.** Must be an existing Vic3 good — check `grep -l "^<good> = {" "$(python3 -c 'from path_constants import base_game_path; print(base_game_path)')/game/common/goods/"*.txt`. The good's name in script is just the bare ID (e.g. `grain`, `small_arms`). Modded-only goods work too if they're registered, but that's rare for SR additions.
2. **Tech gate.** When does this good become available in the SR UI? Mirrors existing precedent:
   - **Always available** (no tech): for war-materiel-from-game-start (grain, small_arms, artillery have this).
   - **Single tech** (the most common): the tech that marks the good as a strategic concern. E.g. `military_aviation` (aeroplanes), `mobile_armor` (tanks), `percussion_cap` (ammunition), `fractional_distillation` (oil). Verify the tech exists: `grep -rE "^<tech> = \{" "$(python3 -c 'from path_constants import base_game_path; print(base_game_path)')/game/common/technology/technologies/"`.
3. **Base annual decay rate.** Fraction of stockpile lost per year. Existing reference: grain=0.25 (perishable food), aeroplanes=0.08 (fabric/engines age), tanks=0.04, small_arms=0.02, ammunition=0.02, artillery=0.015, oil=0.005 (stable). Pick by analogy.
4. **Optional: per-tech decay reduction `INJECT:`s** in `common/technology/technologies/modified.txt`. Existing examples: `canneries`/`vacuum_canning`/`pasteurization`/`flash_freezing`/`lab-grown_food` reduce grain decay; `dynamite`/`military_grade_cybersecurity`/`modern_chemical_processes` reduce ammunition; `fractional_distillation`/`supply_chain_management`/`advanced_workflow_optimization`/`modern_chemical_processes`/`predictive_logistics` reduce oil. Optional polish; skip unless user asks.

## CRITICAL pre-flight: vanilla mult-axis registration gap

**This is the bug class that broke aeroplanes the first time.** Vanilla auto-registers `goods_input_<good>_add` and `goods_output_<good>_add` for every vanilla good, but `goods_input_<good>_mult` and `goods_output_<good>_mult` are **partially registered** — only for the axis combinations vanilla itself uses. The SR hub-flow static modifiers (`st_res_<good>_store_flow` uses `goods_input_<good>_mult`, `st_res_<good>_withdraw_flow` uses `goods_output_<good>_mult`) need BOTH mult axes registered or the modifier silently no-ops and the engine logs `Unknown modifier type: goods_input_<good>_mult` to debug.log.

Before writing the static flow modifiers, run this audit for the new good(s):

```bash
VAN="/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/common/modifier_type_definitions/01_building_modifier_types.txt"
for good in <NEW_GOOD_1> <NEW_GOOD_2>; do
  printf "%-15s input_mult=%s output_mult=%s\n" "$good" \
    "$(grep -c "^goods_input_${good}_mult={" "$VAN")" \
    "$(grep -c "^goods_output_${good}_mult={" "$VAN")"
done
```

`0` = vanilla doesn't register that axis. **Any 0 means you must add a registration entry to `common/modifier_type_definitions/mod_entity_modifier_types.txt`.** The mod already pre-registers `goods_input_grain_mult`, `goods_output_grain_mult`, and `goods_input_aeroplanes_mult` for exactly this reason — follow that pattern (search the file for the existing `goods_input_grain_mult = { color = bad percent = yes ... }` block to see the format).

Reference: `docs/guides/scripting_best_practices.md` § goods modifier registration.

## File layout

All paths relative to `/home/jakef/src/Vic3TimelineExtended/`. The pattern is identical for every good — most lines are mechanical copies. Snippet templates with the `<GOOD>` placeholder live in `references/per_good_templates.md`; this section names every file and what to add.

| # | File | What to add per new good |
|---|---|---|
| 1 | `common/modifier_type_definitions/st_res_modifier_types.txt` | 2 modifier defs: `country_st_res_<GOOD>_capacity_add` (color=good, decimals=0) + `country_st_res_<GOOD>_decay_add` (color=bad, decimals=3, percent=yes) |
| 2 | `common/modifier_type_definitions/mod_entity_modifier_types.txt` | **Only if the pre-flight audit flagged a missing mult axis.** Add the missing `goods_input_<GOOD>_mult` and/or `goods_output_<GOOD>_mult` entry, modeled on the existing `goods_input_grain_mult` block. |
| 3 | `common/static_modifiers/extra_modifiers.txt` | (a) one base decay value in the `INJECT:base_values` block near the top, (b) two hub-flow static modifiers (`st_res_<GOOD>_store_flow` with `goods_input_<GOOD>_mult = 1`, `st_res_<GOOD>_withdraw_flow` with `goods_output_<GOOD>_mult = 1`) added next to the existing `st_res_oil_*_flow` entries near the bottom of the file |
| 4 | `common/production_methods/strategic_reserve_pms.txt` | (a) one capacity line in `pm_st_res_hub_reserve` `country_modifiers > level_scaled` (`country_st_res_<GOOD>_capacity_add = 5000`), (b) two goods-I/O lines in `pm_st_res_hub_reserve` `building_modifiers > workforce_scaled` (`goods_input_<GOOD>_add = 1`, `goods_output_<GOOD>_add = 1`), (c) one capacity line in `pm_st_res_silo_capacity` `country_modifiers > level_scaled` (`country_st_res_<GOOD>_capacity_add = 1000`) |
| 5 | `common/script_values/st_res_script_values.txt` | One full per-good section (10 script values: decay_rate, weekly_decay, actual_rate, actual_rate_base_applied, weekly_delta, capacity, good_mult, max_withdrawable, max_storable, sale_profit) appended after the existing `--- TANKS ---` section, plus one `st_res_<GOOD>_fill_pct` value at the end with the other fill_pct entries. See template. |
| 6 | `common/scripted_effects/st_res_effects.txt` | Eight existing effects extended to enumerate the new good (`st_res_init_effect`, `st_res_reset_vars_effect`, `st_res_clamp_stockpiles_effect`, `st_res_weekly_update_effect`, `st_res_je_immediate_effect`, `st_res_je_weekly_pulse_effect`, `st_res_reset_rates_effect`, `st_res_apply_sell_profit_effect`, plus the cached actual-rate writes in `st_res_refresh_hub_flow_effect`, plus the per-good calls in `st_res_rebuild_hub_flow_modifiers_effect`); add 1 new wrapper effect (`st_res_rebuild_<GOOD>_flow_modifiers_effect` that just calls `st_res_rebuild_good_flow_modifiers_effect = { GOOD = <GOOD> }`) and 2 rate-adjust effects (`st_res_increase_<GOOD>_rate_effect`, `st_res_decrease_<GOOD>_rate_effect`). See template. |
| 7 | `common/scripted_buttons/st_res_buttons.txt` | 2 buttons (`st_res_increase_<GOOD>_rate_button`, `st_res_decrease_<GOOD>_rate_button`) — copy from the existing oil button pair, change the good name everywhere, swap the `has_technology_researched = fractional_distillation` line for the chosen tech (or remove the `has_technology_researched` line entirely if no tech gate). |
| 8 | `common/scripted_progress_bars/st_res_progress_bars.txt` | One `st_res_<GOOD>_fill_bar` block (5 lines, identical structure to the existing oil bar). |
| 9 | `common/customizable_localization/st_res_custom_loc.txt` | One `st_res_<GOOD>_mode_text` block (3 text branches: storing/withdrawing/idle), copy of the oil block with name swapped. |
| 10 | `common/journal_entries/je_strategic_reserve.txt` | 3 wirings: (a) one `scripted_progress_bar = st_res_<GOOD>_fill_bar` line, (b) two `scripted_button = st_res_{increase,decrease}_<GOOD>_rate_button` lines, (c) one `triggered_desc { desc = je_strategic_reserve_<GOOD>_line trigger = { has_technology_researched = <TECH> } }` block in the `status_desc` (use `trigger = { always = yes }` for no-tech-gate goods). |
| 11 | `localization/english/te_modifiers_l_english.yml` | 4 keys: `country_st_res_<GOOD>_capacity_add` + `_desc`, `country_st_res_<GOOD>_decay_add` + `_desc`. Insert in alphabetical position among the existing `country_st_res_*` keys. |
| 12 | `localization/english/te_journal_entries_l_english.yml` | 1 key: `je_strategic_reserve_<GOOD>_line`. Also update `je_strategic_reserve_desc` to add the new good's name to the comma list. |
| 13 | `localization/english/te_miscellaneous_l_english.yml` | 5 keys: `st_res_<GOOD>_fill_bar_name`, `st_res_<GOOD>_store_flow`, `st_res_<GOOD>_withdraw_flow`, `st_res_increase_<GOOD>_rate_button`, `st_res_decrease_<GOOD>_rate_button`. |
| 14 | `localization/english/te_concepts_l_english.yml` | 5 keys: `st_res_<GOOD>_fill_bar_desc`, `st_res_<GOOD>_store_flow_desc`, `st_res_<GOOD>_withdraw_flow_desc`, `st_res_increase_<GOOD>_rate_button_desc`, `st_res_decrease_<GOOD>_rate_button_desc`. |
| 15 | `localization/english/te_buildings_l_english.yml` | (Optional polish) Update `building_strategic_reserve_hub_desc` to include the new good's name in its enumeration, same for `pm_st_res_silo_capacity_desc` in `te_production_methods_l_english.yml`. |

**Conventions enforced by this list:**
- Identifiers use the bare good ID with underscores (`small_arms`, never `smallarms` or `SmallArms`).
- Tab-indented `.txt` files; YAML uses spaces. Run `python scripts/format_paradox_tabs.py --check <files>` before claiming done.
- The existing pattern is established 7× over — when in doubt, grep for an existing good's name in each file (e.g. `grep -n "tanks" common/scripted_effects/st_res_effects.txt`) and clone its block.

## Snippet templates

Open `references/per_good_templates.md` for the verbatim template blocks for files 5 (script values), 6 (effects), 7 (buttons), 8 (bar), 9 (mode text). Each template uses `<GOOD>` (lowercase good ID) and `<GOOD_DISPLAY>` (the prose form: e.g. "Small Arms" for the good_id `small_arms`) as placeholders — copy and substitute.

## Capacity & rate baselines (already established)

These come from `pm_st_res_hub_reserve` and `pm_st_res_silo_capacity` and are **shared across all goods** — every good gets the same per-level capacity:
- Hub: +5000 capacity per level per good.
- Silo: +1000 capacity per level per good.
- Hub weekly rate cap: +1000/level (shared across all goods, not per-good).
- Silo weekly rate cap: +100/level (also shared).

Don't change these for one good in isolation — they're a single global pool. If the user wants asymmetric capacity (e.g. tanks-only silo), that's a different design conversation.

## Verification (every time)

Run all four after the edits, in order:

1. **Parse.** `.venv/bin/python -c "from paradox_file_parser import ParadoxFileParser; p = ParadoxFileParser(); [p.parse_file(f) for f in [<list of edited .txt files>]]; print('OK')"` — catches brace mismatches before the engine sees them.

2. **Reload mod_state_server.** Make sure it's running (`curl -s http://127.0.0.1:8950/status` returns OK; if not, `.venv/bin/python mod_state_server.py &` and wait ~90s). Then `curl -s -X POST http://127.0.0.1:8950/reload`. Cold reload takes 70-110 s.

3. **Engine coverage.** `curl -s http://127.0.0.1:8950/validate/engine-coverage | python3 -c "import json,sys; d=json.load(sys.stdin); print('unknown:', len(d.get('unknown_modifiers',[]))); print('suspicious:', len(d.get('suspicious_modifiers',[])))"`. Both must be 0. Anything non-zero — likely a missed mult-axis registration — go back to the pre-flight section.

4. **debug.log spot check.** `curl -s 'http://127.0.0.1:8950/logs/debug?summary=false&dedupe=true&q=<NEW_GOOD>' | python3 -c "import json,sys; d=json.load(sys.stdin); print('entries:', d.get('total_unique', 0)); [print(e.get('message','')[:200]) for e in d.get('entries',[])]"`. 0 entries is the goal. The debug.log is from the **previous** game session, so this confirms no historical errors; for a true runtime check the user has to launch the game.

## In-game verification caveat (mention this proactively)

The journal entry binds its `scripted_progress_bar` and `scripted_button` declarations **at activation time**. An already-active `je_strategic_reserve` instance (e.g. on a save from before this skill ran) won't pick up the new bars/buttons on script reload. The user must:

1. Demolish the Strategic Reserve Hub building (this fires `on_invalid` → `st_res_je_invalid_effect`, deactivating the JE and resetting all SR vars).
2. Rebuild the hub (re-activates JE, `st_res_je_immediate_effect` re-binds with the full new bar+button set).

The pre-existing **Reset Reserve Rates** button reaches the new goods even on an old JE instance because its effect (`st_res_reset_rates_effect`) is what was updated, not the button itself — a user wanting to neutralize the new goods' hub I/O without rebuilding can click Reset.

## Gotchas

- **Engine modifier-type definitions live in two places.** `st_res_modifier_types.txt` defines the SR-specific country modifiers. `mod_entity_modifier_types.txt` is for goods-mult axes vanilla skipped. Don't conflate them.
- **Don't rename existing goods.** Removing or renaming `grain`/`ammunition`/`oil`/etc. would orphan saved variables (`st_res_<old>_stored`, `_rate`) and require a save-migration effect. The existing system is additive-only by design.
- **Adding a NEW non-vanilla good** (e.g. a mod-only good called `helium`) is in scope, but ALSO requires registering `goods_input_<good>_add` / `goods_output_<good>_add` in `mod_entity_modifier_types.txt` because the good itself isn't in vanilla. Confirm the good exists before treating this as an SR-only task.
- **The `disable_input_flow` / `disable_output_flow` static modifiers** that exist for grain/ammunition in `extra_modifiers.txt` are dead code (no effect references them). Don't add new ones for the new goods — store_flow + withdraw_flow are sufficient. The else-branch of `st_res_rebuild_good_flow_modifiers_effect` applies these two with `multiplier = -1` to neutralize the hub PM's base 1-unit goods I/O when the good is idle (rate=0), which is the only thing that matters.

## Reference

- `references/per_good_templates.md` — verbatim per-good snippet bodies for files 5–9.
- `docs/guides/scripting_best_practices.md` § goods modifier registration — the mult-axis registration rule.
- `docs/systems/mod_systems.md` § Strategic Reserve — high-level system overview.
