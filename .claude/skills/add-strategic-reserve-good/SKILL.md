---
name: add-strategic-reserve-good
description: Add one or more new goods to the Strategic Reserve journal entry in the Vic3TimelineExtended mod (the JE that lets a country stockpile strategic goods in a Hub building). Use whenever the user mentions extending, adding to, or putting a new good into the Strategic Reserve / SR system / `je_strategic_reserve` — phrases like "add gold to the reserve", "extend SR to cover steel", "add a new strategic reserve good", "let players stockpile X". Also triggers when the user wants to change which goods the SR Hub buys/sells or adds a new good row to that journal's reserve inventory widget. Touches ~14 files in a strict per-good pattern; this skill walks through every one and surfaces the vanilla mult-axis registration gap that silently breaks new goods otherwise.
---

# Add a strategic-reserve good

## When to use

The Strategic Reserve is a country-scoped stockpile system anchored on `je_strategic_reserve` and the `building_strategic_reserve_hub` building. Each covered good has its own stored stockpile, configurable weekly storage/withdraw rate, decay rate, an optional **price-triggered policy** that re-decides that rate weekly, and one row in the **reserve inventory widget** (`gui/journal_entry_widgets/strategic_reserve_widget.gui`) carrying its fill bar, net weekly movement, status label, decrease/stop/increase controls, policy summary and a collapsible settings panel. The system already covers `grain`, `ammunition`, `oil`, `small_arms`, `artillery`, `aeroplanes`, `tanks`, `fertilizer` (displayed as Chemicals). Adding any new good touches ~14 files with a strict copy-paste-modify pattern — miss one and the good silently does nothing in-game.

**Read this if you last worked on the SR before the inventory widget:** per-good `scripted_progress_bar`s, per-good `scripted_button`s and per-good journal-entry `status_desc` lines are **gone**. A good is now surfaced by an unlock scripted trigger, **two** scripted GUIs, a widget row and **four** customizable-localization blocks. Don't re-add the old shapes.

**Read this if you last worked on the SR before reserve policies:** a good also needs `st_res_policy_<GOOD>_sgui`, the `st_res_<GOOD>_policy_text` / `_policy_reason_text` custom loc, ten policy script values, its policy-panel blockoverrides in the widget row, and one line in `st_res_ai_seed_policies_effect`. The twelve per-good policy settings (and the running price average the smoothing keeps) are seeded and reset by effects that are already `$GOOD$`-parameterized, so they need no new code.

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
VAN="$(python3 -c 'import path_constants; print(path_constants.base_game_path)')/game/common/modifier_type_definitions/01_building_modifier_types.txt"
for good in <NEW_GOOD_1> <NEW_GOOD_2>; do
  printf "%-15s input_mult=%s output_mult=%s\n" "$good" \
    "$(grep -c "^goods_input_${good}_mult={" "$VAN")" \
    "$(grep -c "^goods_output_${good}_mult={" "$VAN")"
done
```

`0` = vanilla doesn't register that axis. **Any 0 means you must add a registration entry to `common/modifier_type_definitions/mod_entity_modifier_types.txt`.** The mod already pre-registers `goods_input_grain_mult`, `goods_output_grain_mult`, `goods_input_aeroplanes_mult` and `goods_input_fertilizer_mult` for exactly this reason — follow that pattern (search the file for the existing `goods_input_grain_mult = { color = bad percent = yes ... }` block to see the format).

Reference: `docs/guides/scripting_best_practices.md` § goods modifier registration.

## File layout

All paths are repo-relative (`mod_path` in `path_constants`). The pattern is identical for every good — most lines are mechanical copies. Snippet templates with the `<GOOD>` placeholder live in `references/per_good_templates.md`; this section names every file and what to add.

| # | File | What to add per new good |
|---|---|---|
| 1 | `common/modifier_type_definitions/st_res_modifier_types.txt` | 2 modifier defs: `country_st_res_<GOOD>_capacity_add` (color=good, decimals=0) + `country_st_res_<GOOD>_decay_add` (color=bad, decimals=3, percent=yes) |
| 2 | `common/modifier_type_definitions/mod_entity_modifier_types.txt` | **Only if the pre-flight audit flagged a missing mult axis.** Add the missing `goods_input_<GOOD>_mult` and/or `goods_output_<GOOD>_mult` entry, modeled on the existing `goods_input_grain_mult` block. |
| 3 | `common/static_modifiers/extra_modifiers.txt` | (a) one base decay value in the `INJECT:base_values` block near the top, (b) two hub-flow static modifiers (`st_res_<GOOD>_store_flow` with `goods_input_<GOOD>_mult = 1`, `st_res_<GOOD>_withdraw_flow` with `goods_output_<GOOD>_mult = 1`) added next to the existing `st_res_oil_*_flow` entries near the bottom of the file |
| 4 | `common/production_methods/strategic_reserve_pms.txt` | (a) one capacity line in `pm_st_res_hub_reserve` `country_modifiers > level_scaled` (`country_st_res_<GOOD>_capacity_add = 5000`), (b) two goods-I/O lines in `pm_st_res_hub_reserve` `building_modifiers > workforce_scaled` (`goods_input_<GOOD>_add = 1`, `goods_output_<GOOD>_add = 1`), (c) one capacity line in `pm_st_res_silo_capacity` `country_modifiers > level_scaled` (`country_st_res_<GOOD>_capacity_add = 1000`) |
| 5 | `common/script_values/st_res_script_values.txt` | One full per-good section (10 script values: decay_rate, weekly_decay, actual_rate, actual_rate_base_applied, weekly_delta, capacity, good_mult, max_withdrawable, max_storable, sale_profit) appended after the existing `--- TANKS ---` section, plus **two** widget accessors at the end with their siblings: `st_res_<GOOD>_fill_pct` and `st_res_<GOOD>_last_net`, plus **ten** reserve-policy values (`_price_up`, `_price_down`, `_price_rel`, `_price_signal`, `_unit_price`, the four `_policy_*_limit` stepper guards, and `_policy_budget_max`, the budget stepper's ceiling). The two accessors and `_price_signal` **must be `has_variable`-guarded** — the widget evaluates them every frame. See template. |
| 6 | `common/scripted_triggers/st_res_triggers.txt` | 1 trigger: `st_res_<GOOD>_unlocked_trigger`, holding the tech gate (or `always = yes`). This is the only place the unlock condition may live. |
| 7 | `common/scripted_effects/st_res_effects.txt` | Add the good to six per-good call lists (`st_res_init_effect`, `st_res_reset_vars_effect`, `st_res_rebuild_hub_flow_modifiers_effect` — both halves, `st_res_weekly_update_effect` — both branches, `st_res_refresh_hub_flow_effect` — cached rate write **and** status call); add `st_res_policy_tick_good_effect = { GOOD = <GOOD> }` to **both** branches of `st_res_weekly_update_effect`, `st_res_switch_to_manual_base` to `st_res_reset_rates_effect` and `st_res_ai_seed_good_effect` to `st_res_ai_seed_policies_effect`; extend `st_res_clamp_stockpiles_effect`, `st_res_reset_rates_effect`, `st_res_apply_sell_profit_effect`; add 4 wrapper effects (`st_res_rebuild_<GOOD>_flow_modifiers_effect`, `st_res_{increase,decrease,stop}_<GOOD>_rate_effect`). See template. |
| 8 | `common/scripted_guis/st_res_scripted_gui.txt` | **2** scripted GUIs: `st_res_adjust_<GOOD>_sgui`, with `saved_scopes = { dir }` (0 decrease / 1 stop / 2 increase), and `st_res_policy_<GOOD>_sgui`, with `saved_scopes = { op }` (the op-code table is in the file header). Copy the grain blocks and swap the good name — do not hand-write the 20-branch `is_valid`. |
| 9 | `common/customizable_localization/st_res_custom_loc.txt` | **4** blocks: `st_res_<GOOD>_mode_text` (4 branches on `st_res_<GOOD>_last_status`), `st_res_<GOOD>_reason_text` (9 branches), `st_res_<GOOD>_policy_text` (4 branches on `st_res_<GOOD>_policy`) and `st_res_<GOOD>_policy_reason_text` (10 branches on `st_res_<GOOD>_policy_status`). Copy the grain set. |
| 10 | `gui/journal_entry_widgets/strategic_reserve_widget.gui` | 1 `widget_je_st_res_inventory_row` instance in the root flowcontainer: datacontext + visible + tooltip + 8 blockoverrides, the last of which nests a `widget_je_st_res_policy_panel` with its datacontext, visibility key and 8 value cells. **No `type` needs to change** — the policy panel's op codes are identical for every good. |
| 11 | `common/journal_entries/je_strategic_reserve.txt` | **Nothing.** No per-good bar, button or status line exists any more. |
| 12 | `localization/english/te_modifiers_l_english.yml` | 4 keys: `country_st_res_<GOOD>_capacity_add` + `_desc`, `country_st_res_<GOOD>_decay_add` + `_desc`. Insert in alphabetical position among the existing `country_st_res_*` keys. |
| 13 | `localization/english/te_journal_entries_l_english.yml` | No new key. Update `je_strategic_reserve_desc` to add the new good's name to the comma list. |
| 14 | `localization/english/te_miscellaneous_l_english.yml` | 8 keys: `st_res_<GOOD>_store_flow`, `st_res_<GOOD>_withdraw_flow`, `st_res_row_<GOOD>_name`, `st_res_row_<GOOD>_amount`, `st_res_row_<GOOD>_status`, `st_res_row_<GOOD>_flow`, `st_res_row_<GOOD>_policy`, `st_res_row_<GOOD>_policy_reason`. Every other policy string (policy names, presets, settings labels, tooltips, all ten explanations) is shared and already exists. |
| 15 | `localization/english/te_concepts_l_english.yml` | 3 keys: `st_res_<GOOD>_store_flow_desc`, `st_res_<GOOD>_withdraw_flow_desc`, `st_res_row_<GOOD>_tooltip`. |
| 16 | `localization/english/te_buildings_l_english.yml` | (Optional polish) Update `building_strategic_reserve_hub_desc` to include the new good's name in its enumeration, same for `pm_st_res_silo_capacity_desc` in `te_production_methods_l_english.yml`. |

**Goods texticon.** The row name and tooltip header use `@<GOOD>!`. Vanilla goods already have one (`grep -n "icon = <GOOD>$" "$VIC3/game/gui/goods_texticons.gui"`); a mod-only good needs an entry added to `gui/zzz_extra_goods_texticons.gui` or the icon renders as literal text.

**Conventions enforced by this list:**
- Identifiers use the bare good ID with underscores (`small_arms`, never `smallarms` or `SmallArms`).
- Tab-indented `.txt` files; YAML uses spaces. Run `python scripts/format_paradox_tabs.py --check <files>` before claiming done.
- The existing pattern is established 8× over — when in doubt, grep for an existing good's name in each file (e.g. `grep -n "tanks" common/scripted_effects/st_res_effects.txt`) and clone its block.

## Snippet templates

Open `references/per_good_templates.md` for the verbatim template blocks for files 5 (script values), 6 (unlock trigger), 7 (effects), 8 (scripted GUI), 9 (custom loc), 10 (widget row) and the localization keys. Each template uses `<GOOD>` (lowercase good ID) and `<GOOD_DISPLAY>` (the prose form: e.g. "Small Arms" for the good_id `small_arms`) as placeholders — copy and substitute.

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

The widget's rows are plain GUI, so a new good's row **does** appear immediately on script reload — no rebuild needed for the UI. What still needs care:

- `st_res_<GOOD>_last_delta` / `st_res_<GOOD>_last_status` do not exist until `st_res_init_effect` runs (JE activation or the next weekly pulse). Until then the row reads "Idle" with net 0. That is intentional and save-safe; wait a week of in-game time before judging the numbers.
- The journal entry still binds `scripted_button` declarations at **activation** time, so if you ever change the two shared buttons the user must demolish and rebuild the hub for them to re-bind.
- The **Reset Reserve Rates** button reaches new goods even on an old JE instance, because its effect (`st_res_reset_rates_effect`) is what was updated, not the button itself.

Things only a running game can confirm for a new good: the goods texticon actually renders, the row fits the panel width, the fill bar tracks the stockpile, and the three controls move only that good's rate.

## Gotchas

- **Engine modifier-type definitions live in two places.** `st_res_modifier_types.txt` defines the SR-specific country modifiers. `mod_entity_modifier_types.txt` is for goods-mult axes vanilla skipped. Don't conflate them.
- **Don't rename existing goods.** Removing or renaming `grain`/`ammunition`/`oil`/etc. would orphan saved variables (`st_res_<old>_stored`, `_rate`) and require a save-migration effect. The existing system is additive-only by design.
- **Adding a NEW non-vanilla good** (e.g. a mod-only good called `helium`) is in scope, but ALSO requires registering `goods_input_<good>_add` / `goods_output_<good>_add` in `mod_entity_modifier_types.txt` because the good itself isn't in vanilla. Confirm the good exists before treating this as an SR-only task.
- **The `disable_input_flow` / `disable_output_flow` static modifiers** that exist for grain/ammunition in `extra_modifiers.txt` are dead code (no effect references them). Don't add new ones for the new goods — store_flow + withdraw_flow are sufficient. The else-branch of `st_res_rebuild_good_flow_modifiers_effect` applies these two with `multiplier = -1` to neutralize the hub PM's base 1-unit goods I/O when the good is idle (rate=0), which is the only thing that matters.
- **Never re-derive a good's status in GUI or loc.** `st_res_set_good_status_effect` is the only place the Storing / Withdrawing / Idle / Blocked state and its reason are decided; the widget and the custom loc only read `st_res_<GOOD>_last_status`. Same for net movement: `st_res_apply_weekly_good_effect` records the post-clamp delta, and the widget reads it. If you find yourself writing a rate comparison in a `.gui` expression, stop.
- **`dir` and `op` are implicit contracts.** The widget passes `AddScope('dir', …)` / `AddScope('op', …)` and the scripted GUIs branch on `scope:dir` / `scope:op`. `dir`: 0 decrease, 1 stop, 2 increase. `op`: 0-3 select policy, 10-12 preset, 20-35 the eight steppers (32/33 price memory, 34/35 response ramp), 44/45 · 64/65 and 50/51 · 70/71 the shift- and ctrl-click steps of maximum weekly flow and weekly budget. The sgui header, the widget header and `docs/systems/strategic_reserve_system.md` §5 all carry the tables — keep all three in sync.
- **The Strategic Reserve is no longer player-only, but its UI is.** Every SR button still carries `ai_chance = { value = 0 }` and both scripted GUIs carry `ai_is_valid = { always = no }` — those exist to validate *player* clicks. The AI reaches the reserve through script instead: `building_strategic_reserve_hub` has a real `ai_value` (+50 major/GP, +150 at war, `common/buildings/strategic_reserve.txt`), so AI majors build hubs, and `st_res_ai_seed_policies_effect` hands them the Conservative preset once. **A new good must be added to that effect** or the AI will simply never touch it. Don't give a good an AI path through a button or an sgui.
- **`st_res_policy_tick_good_effect` goes in BOTH branches of the weekly pulse.** It advances the good's running price average and then calls `st_res_policy_evaluate_good_effect`, the single derivation site for `st_res_<GOOD>_policy_status`, whose no-hub branch is what writes status 9. In the hub branch it sits *after* the `st_res_apply_weekly_good_effect` loop and *before* the shared refresh/clamp tail. The policy panel's click path calls the **evaluator** directly, never the tick — a click must not advance the price average.
- **The evaluator reads `st_res_<GOOD>_price_signal`, never the live price.** That is the running average (or the live price until the first tick seeds it). Reading `_price_rel` in the evaluator would silently defeat the smoothing for that good.
- **Automation writes rates only through `st_res_apply_rate_target_base`.** Never let a policy path call `st_res_{increase,decrease,stop}_<GOOD>_rate_effect` — those deliberately switch the good to Manual, so a policy calling one would cancel itself on its first tick.
- **Don't simplify the price signal.** `st_res_<GOOD>_price_rel` is `max(pricier,0) - max(cheaper,0)` on purpose; a bare `market_goods_pricier` read is only correct if the engine returns signed values, which the docs don't state. See `docs/systems/strategic_reserve_system.md` §4.6.

## Reference

- `references/per_good_templates.md` — verbatim per-good snippet bodies for files 5–10 and the loc keys.
- `docs/systems/strategic_reserve_system.md` — the system reference (§4 status codes, §5 panel layout, §7 AI).
- `docs/guides/scripting_best_practices.md` § goods modifier registration — the mult-axis registration rule.
- `docs/guides/gui_modding_guide.md` § "One scripted GUI, several buttons" — the `AddScope` parameterization pattern the row controls use.
