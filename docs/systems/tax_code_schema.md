# Legislated tax code: canonical state and the collection writer

The variable schema of the legislated tax code (spec: `docs/superpowers/specs/2026-09-29-legislated-tax-code-design.md`; plan: `docs/superpowers/plans/2026-10-02-legislated-tax-code-tasks.md`), the one effect that turns it into native tax settings, the scheduler that changes it on its dates, and the display values that read it. Later tasks extend the schema tables and the sections below; `test_tax_code_state.py` parses the tables and checks them against the initialiser.

Everything here runs only under `te_tax_code_rule` (`te_tax_code_on = yes`). With the rule off no variable is written and no native setting is touched.

## Conventions

- **Country variables, fixed names.** The enacted code is plain numeric country variables, one per schema row. No lists and no containers: a civil war's winner keeps neither.
- **Tokens are never removed.** "Empty" is the row's sentinel, written with `set_variable`. A winner inherits every loser variable it does not itself hold, so a removed token would come back holding the loser's value (CLAUDE.md "Top gotchas"). No file of the tax code may `remove_variable` a schema token; `test_tax_code_state.py` scans for it.
- **Indices, not rates.** Each instrument is an integer index; rate = index × `te_tax_step_<key>` (`scripts/generators/gen_tax_code.py`, `INSTRUMENTS`). Index 0 means not collected. Unset or unchanged fields of a draft, bill or package are `-1`.
- **Months are absolute.** A month is a `te_history_month_index` value (`year × 12 + month`, January = 0; `common/script_values/te_history_values.txt`). No `_y`/`_mo` variables are stored: the display values split a month into a year and a 1-based month with `floor`, which a script value can do and a GUI cannot.

## Schema

| Variable | Meaning | Sentinel |
|---|---|---|
| `te_tax_schema` | schema version, = 1 | — |
| `te_tax_migrated` | migration version applied (Task 5) | 0 |
| `te_tax_code_version` | +1 on every enacted change | 0 |
| `te_tax_last_month` | scheduler once-per-month guard | -1 |
| `te_tax_next_month` | earliest due transition month (cache) | -1 |
| `te_tax_en_<key>` | enacted index per instrument (`wage div land head cons`) | 0 |
| `te_tax_en_<key>_since` | month the current value became operative | -1 |
| `te_tax_en_<key>_exp` | sunset month of the current value | -1 |
| `te_tax_en_<key>_succ` | successor index at sunset | -1 |
| `te_tax_pver_<key>` | planned-version token: +1 whenever an approval or unexpected change touches the provision | 0 |
| `te_tax_xver_<key>` | external-change token: +1 only on non-legislative changes (migration re-run, civil-war repair) | 0 |
| `te_tax_en_g_<good>` | 1 if the good is on the enacted taxed-goods list | 0 |
| `te_tax_pver_goods`, `te_tax_xver_goods` | tokens for the goods group | 0 |
| `te_tax_en_agrel` | agricultural wage relief index: 0 none, 1 = −25%, 2 = −50% | 0 |
| `te_tax_en_regrel` | regional relief depth: 0 none, 1 = −25%, 2 = −50% | 0 |
| state var `te_tax_relief_state` | 1 on states named in the enacted regional relief (max 3 per country) | 0 |
| `te_tax_pver_relief`, `te_tax_xver_relief` | tokens for relief | 0 |

`<key>` is one of `wage div land head cons`; `<good>` is one of the [catalog](#consumption-goods-catalog) goods.

| Instrument | `<key>` | Native modifier | Step | Max index |
|---|---|---|---|---|
| Wage tax | `wage` | `tax_income_add` | 0.025 | 20 |
| Dividend tax | `div` | `tax_dividends_add` | 0.025 | 20 |
| Rural assessment | `land` | `tax_land_add` | 0.025 | 48 |
| Head tax | `head` | `tax_per_capita_add` | 0.05 | 30 |
| Consumption tax rate | `cons` | `tax_consumption_add` | 0.05 | 12 |

### Package slots, history ring and clock

The [scheduler](#scheduler-package-slots-and-history)'s rows. `<s>` is a package slot, `a` or `b`; `<n>` a history entry, 1 to 8. A sentinel of "—" marks a package's payload: it is not initialised, because `te_tax_store_package` writes every payload field of a slot when it fills it and nothing reads the payload while `te_tax_p<s>_on` is 0. A civil war's winner may inherit a loser's payload for a slot it never filled; it stays unread for the same reason.

| Variable | Meaning | Sentinel |
|---|---|---|
| `te_tax_now` | the month index the last scheduler run read, set at its start | -1 |
| `te_tax_p<s>_on` | 1 while slot `<s>` holds an approved package; the slot is free at 0 | 0 |
| `te_tax_p<s>_due` | commencement month | -1 |
| `te_tax_p<s>_state` | 1 awaiting, 2 held_conflict, 3 held_missed; 0 once commenced or never filled | 0 |
| `te_tax_p<s>_seq` | approval sequence: one above both slots when stored; the lower commences first in a shared month | 0 |
| `te_tax_p<s>_<key>` | the provision's new index, -1 if the package leaves it alone | — |
| `te_tax_p<s>_<key>_exp` | the new value's sunset month (due + offset), -1 for none | — |
| `te_tax_p<s>_<key>_succ` | the index the sunset restores, -1 for none | — |
| `te_tax_p<s>_xver_<key>` | `te_tax_xver_<key>` when the bill recorded it | — |
| `te_tax_p<s>_g_<good>` | 1 tax the good, 0 stop taxing it, -1 leave it alone | — |
| `te_tax_p<s>_xver_goods` | `te_tax_xver_goods` when the bill recorded it | — |
| `te_tax_p<s>_agrel`, `te_tax_p<s>_regrel` | new relief depth, -1 if left alone | — |
| `te_tax_p<s>_regrel_states_set` | 1 when the package restates the regional-relief states (`te_tax_p<s>_regrel` ≥ 0) | — |
| `te_tax_p<s>_xver_relief` | `te_tax_xver_relief` when the bill recorded it | — |
| state var `te_tax_pending_relief_<s>` | 1 on an owned state the package in slot `<s>` names for regional relief | 0 |
| `te_tax_h_head` | the history entry holding the newest event; 0 while the ring is empty | 0 |
| `te_tax_h<n>_month` | month of the event | -1 |
| `te_tax_h<n>_kind` | 1 commenced, 2 sunset, 3 held_conflict, 4 held_missed, 5 migrated, 6 approved, 7 civil-war repair, 8 superseded; 0 empty | 0 |
| `te_tax_h<n>_slot` | package slot (`te_tax_slot_id_<s>`): 1 `a`, 2 `b`, 0 none | 0 |
| `te_tax_h<n>_inst` | the instrument a sunset changed, 1 wage, 2 div, 3 land, 4 head, 5 cons; 0 for any other kind | 0 |
| `te_tax_h<n>_version` | `te_tax_code_version` after the event | -1 |

## Initialisation

`te_tax_init_country` (country scope, `common/scripted_effects/te_tax_state_effects.txt`) writes every country row above that is absent, with its sentinel, and never touches one that exists. The per-instrument, per-good and scheduler rows come from the generated `te_tax_gen_init_instruments`, `te_tax_gen_init_goods` and `te_tax_gen_init_schedule` (`common/scripted_effects/te_tax_generated_effects.txt`). `te_tax_schema = 1` is written last, so a country holding `te_tax_schema` holds every token of that schema version. Each write has the shape `if = { limit = { NOT = { has_variable = X } } set_variable = { name = X value = <sentinel> } }`, which `je_immediate_reset_audit` accepts if a journal entry's `immediate` ever calls it. The state variables `te_tax_relief_state` and `te_tax_pending_relief_<s>` are not initialised: a state without them is named in no relief.

Callers: the migration (Task 5) before it maps the vanilla law, and the writer below, which re-runs it each time so a later schema version's new rows are backfilled on old saves. A later schema bumps the version in a guarded `else_if` after the new rows, never by overwriting the old value unconditionally.

`te_tax_copy_token = { NAME = <token> }` copies one token from `scope:te_tax_source` to THIS when the source holds it, for the civil-war outbreak copy (Task 10).

## The collection writer

`te_tax_sync_collection` (`common/scripted_effects/te_tax_collection_effects.txt`) is the **only** effect that changes a rule-on country's native fiscal state. Nothing else in `common/` or `events/` (apart from the temporary probe harness, `te_debug_tax*`) calls `add_amendment` with a tax-code amendment, `add_taxed_goods`, `remove_taxed_goods`, `set_tax_level` or adds a `te_tax_relief_*` modifier; `test_tax_code_state.py` checks this.

- **Scope.** Country, with ROOT = THIS = the country. Call it from a country event or a country hook (Task 4's dispatched monthly event `te_tax.1`, Task 5's migration event), never from the global `on_monthly_pulse`, which has no ROOT. Nothing in it reads ROOT.
- **Gate.** `te_tax_code_on = yes`, `has_law = law_type:law_te_tax_code` and `has_variable = te_tax_schema`. A country still on a vanilla law is left alone. One holding the carrier without initialised tokens (a rebel before the outbreak copy) is left alone too, rather than synced to an empty code, and logged (`TE_TAX sync skipped: <country> ...` in `debug.log`).
- **Order.** `te_tax_init_country` (backfill); `save_scope_as = te_tax_country`; `te_tax_pick_sponsor` (`scope:te_tax_sponsor`: a random interest group in government if `any_interest_group = { is_in_government = yes }`, else the one with the most clout; it branches on THIS country's groups, never on whether the scope already exists, so a sponsor saved for another country in the same execution cannot leak in); the five `te_tax_gen_sync_<key>`, only when the country has an interest group at all (otherwise one `debug_log` and the amendments stay as they were); `te_tax_gen_sync_goods`; `te_tax_sync_relief`; the tax level pinned to `medium` if it is anything else.
- **Call at most once per effect execution; a second call in a later execution changes nothing.** Amendment, goods and modifier changes are not visible later in the same execution, so a second call there would act on the stale state and could add an amendment twice. Across executions it is idempotent, diff not churn: each part removes only what the code does not hold and adds only what the code holds and is missing. Within the one call no part re-reads what it has just written, and the removal loop never touches the amendment the add step checks.
- **Per-instrument sync** (generated): from `active_law:lawgroup_taxation`, `every_scope_amendment` removes each amendment for which `te_tax_amendment_is_<key>` holds and `te_tax_amendment_matches_<key>` does not; then one `if`/`else_if` branch per index adds `amendment_te_tax_<key>_<idx>` when `var:te_tax_en_<key> = idx` and the law lacks it (`has_amendment`), with `sponsor = scope:te_tax_sponsor cooldown = 0`.
- **Goods sync** (generated): per catalog good, `add_taxed_goods` when `te_tax_en_g_<good> = 1` and the good is not taxed, `remove_taxed_goods` when the flag is not 1 and it is; per good outside the catalog, `remove_taxed_goods` when it is taxed. So the native taxed set equals the enacted set for every good, vanilla and mod.
- **Relief sync**: `te_tax_relief_ag_<n>` on the country for `te_tax_en_agrel = n`; on every owned state with `te_tax_relief_state = 1`, `te_tax_relief_region_<n>` for `te_tax_en_regrel = n`; the other band, or both, removed where present. Each `add_modifier` is guarded by `NOT = { has_modifier }`, each `remove_modifier` by `has_modifier`.
- **Not touched**: tariffs and subventions (customs legislation, Task 15), Millet System / People of the Book heathen tax and `amendment_redemption_payments` (external, held at the pinned medium level), consumption-tax Authority costs.

### Engine forms

The amendment forms are the ones the tax probe used in game (`common/scripted_effects/te_debug_tax_effects.txt:20-44`; add, remove and rebuild worked in R3, `docs/testing/tax-code-probe-results-2026-10-02.md`) and are documented in the 1.14.5 engine logs: `has_amendment = amendment_type:X` (law scope), `type = amendment_type:X` in amendment scope (the `type` link, `event_targets.log`), `every_scope_amendment` from law scope, `remove_amendment = yes`, `add_amendment = { type sponsor cooldown }`. The plan's `is_amendment_type` is not an engine trigger and is not used; nor is `any_scope_amendment` (documented, but not probe-tested). R3 removed probe amendments that had no `can_repeal`. The production amendments carry `can_repeal = { always = no }`; a script `remove_amendment` is expected to ignore it, as it ignores the cooldown, but that is not verified in game. Relief and goods use `has_modifier`, `add_modifier = { name }`, `remove_modifier`, `has_consumption_tax`, `add_taxed_goods`, `remove_taxed_goods`; the level uses `tax_level` and `set_tax_level`.

## Consumption goods catalog

The goods a code can put on its taxed-goods list, derived by `gen_tax_code.py` (`consumption_catalog()`): every good a pop need buys (vanilla `vanilla_parsed/common/pop_needs.json` and the mod's `common/pop_needs/*.txt`, with `REPLACE:`/`INJECT:` applied). A good without a `consumption_tax_cost` costs the engine default (`DEFAULT_GOODS_TAX_COST = 100`, 1.14.5 `common/defines/00_defines.txt`) and is still taxable: vanilla history taxes liquor, tobacco, opium and wine, none of which sets one, and the local goods services, transportation and electricity are taxable. One `te_tax_en_g_<good>` token, one sync branch and one display value per catalog good. Every other good (`stray_goods()`, from vanilla `goods.json` plus the mod's `common/goods/*.txt`) gets only a removal branch in the goods sync. A change to the pop needs or goods files changes the catalog on the next `gen_tax_code.py` run, and `gen_tax_code.py --check` fails until it is run.

**Catalog (39 goods):** `aeroplanes`, `automobiles`, `clippers`, `clothes`, `coal`, `coffee`, `consumer_appliances`, `digital_access`, `digital_assets`, `electricity`, `fabric`, `fine_art`, `fish`, `fruit`, `furniture`, `glass`, `grain`, `groceries`, `liquor`, `luxury_clothes`, `luxury_furniture`, `meat`, `oil`, `opium`, `paper`, `porcelain`, `radios`, `services`, `silk`, `small_arms`, `steamers`, `sugar`, `tea`, `telephones`, `tobacco`, `tourism`, `transportation`, `wine`, `wood`.

**Outside the catalog (26 goods, removed by the sync if natively taxed):** `advanced_materials`, `ammunition`, `artillery`, `construction`, `dye`, `electronic_components`, `engines`, `explosives`, `fertilizer`, `gold`, `hardwood`, `iron`, `ironclads`, `launch_capacity`, `lead`, `magnetic_drive_ships`, `manowars`, `merchant_marine`, `motor_ships`, `robotics`, `rubber`, `steel`, `sulfur`, `tanks`, `tech_metals`, `tools`.

No pop need buys a good outside the catalog (`construction`, consumption-tax cost 400, is bought only by buildings), so a code never taxes one.

## Display values

Guarded reads for the GUI and loc. Each `te_tax_view_*` tests every variable it reads with `has_variable` and returns the row's sentinel when it is absent: 0 for an index, a rate, a flag or a counter; -1 for a month or a successor index. None writes a variable or iterates anything, so a panel can read them freely.

- `common/script_values/te_tax_display_values.txt`: `te_tax_view_schema`, `te_tax_view_migrated`, `te_tax_view_code_version`, `te_tax_view_last_month`, `te_tax_view_next_month`, `te_tax_view_agrel` and `te_tax_view_agrel_pct`, `te_tax_view_regrel` and `te_tax_view_regrel_pct` (band × `te_tax_relief_pct_step` = 25), and `te_tax_view_relief_state` (state scope).
- `common/script_values/te_tax_generated_values.txt` (generated), per instrument: `te_tax_view_en_<key>` (index), `_rate` (index × step), `_pct` (index × percentage-point step; wage, dividend and consumption only), `_since`, `_since_y`, `_since_mo`, `_exp`, `_exp_y`, `_exp_mo`, `_succ`, `_succ_rate`, `_succ_pct` (percent instruments). Per catalog good: `te_tax_view_en_g_<good>`. And `te_tax_view_goods_count`, the number of catalog goods the code taxes.

## Scheduler, package slots and history

An approved package waits in slot `a` or `b` and takes effect on the 1st of its due month; an enacted value with a sunset reverts to its successor. All transitions run in `te_tax_process_month` (`common/scripted_effects/te_tax_schedule_effects.txt`), once per country per calendar month.

### Dispatch

- **Global `on_monthly_pulse`, the 1st of every month** (`common/on_actions/te_tax_on_actions.txt`, `te_tax_monthly_dispatch`). If `te_tax_code_on = yes`, it raises the hidden country event `te_tax.1` (`events/te_tax_internal_events.txt`) on every country with `te_tax_migrated > 0`; `te_tax.1` runs `te_tax_process_month` with ROOT = that country. The country pulse is not used for this: `on_monthly_pulse_country` is a 30-day timer that can skip a calendar month (`docs/guides/scripting_best_practices.md`, "`on_monthly_pulse_country` Is a 30-Day Timer, Not a Calendar Month"), which is how the tax probe commenced and expired a package in one call. Task 5 adds a second branch to the dispatch for countries not yet migrated.
- **Watchdog: `on_monthly_pulse_country`** (`te_tax_watchdog_on_action`). When `te_tax_last_month` < the month index and 0 ≤ `te_tax_next_month` ≤ the month index, it raises `te_tax.2`, which runs `te_tax_watchdog_month`: it logs `TE_TAX watchdog`, runs the sunsets, holds as missed any awaiting package whose due month has passed, and syncs collection. It **never commences** and **never claims the month** (`te_tax_last_month`): a country's pulse can land on the 1st before the global pulse, and claiming the month there would make that day's dispatch skip the month's commencements. Sunsets are safe to run twice in one month, because an executed sunset clears its own `_exp`. A due commencement the watchdog sees becomes held_missed only once its month has passed, by the next processor or watchdog run.

### Processor rules

1. `set_variable = { name = te_tax_now value = te_history_month_index }` once; if `te_tax_last_month >= te_tax_now` stop (a second call in a month does nothing); else `te_tax_last_month = te_tax_now`, before any transition.
2. **Sunsets first** (`te_tax_gen_sunset_<key>`). For each instrument with `te_tax_en_<key>_exp` ≠ -1 and ≤ now: if `te_tax_en_<key>_since < te_tax_now` (`_since < now`), set `te_tax_en_<key> = _succ`, `_since = now`, `_exp = -1`, `_succ = -1`, `te_tax_code_version` +1, history kind 2 with the instrument in `_inst`; otherwise leave it (it runs next month). Late sunsets catch up. A sunset whose `_succ` is -1 is corrupt: its `_exp` is reset to -1 with no version change, so it cannot hold `te_tax_next_month` in the past.
3. **Commencements** in `seq` order, lower first, slot `a` on a tie (`te_tax_gen_commence_<s>`). For a slot with `_on = 1` and `_state = 1`: if `_due = now` (equality, never `>=`): if every touched provision's `te_tax_p<s>_xver_<key>` equals the current `te_tax_xver_<key>`, and likewise `_xver_goods` when the package touches a good and `_xver_relief` when it touches relief (`te_tax_gen_package_current_<s>`), apply every touched field (`te_tax_gen_apply_<s>`: `te_tax_en_<key> = new`, `_since = now`, `_exp`/`_succ` from the package; goods; relief depths; regional-relief states when `_regrel_states_set = 1`), `te_tax_code_version` +1, history kind 1, `_on = 0`, `_state = 0`; else `_state = 2` (held_conflict), history kind 3, the whole package held and collections unchanged. If `_due < now`: `_state = 3` (held_missed), history kind 4; a package is never applied late. A held package waits for explicit rescheduling (Task 6). Commencement does not check the carrier law: the canonical code changes either way, and `te_tax_sync_collection` writes collection only while the country holds `law_te_tax_code`.
4. `te_tax_sync_collection` once, every processed month, whether or not anything changed: it applies the month's transitions and re-asserts the code over any native change since the last month (Task 9 adds drift counters).
5. `te_tax_recompute_next_month`: `te_tax_next_month` = the earliest enacted `_exp` ≥ 0 and awaiting slot `_due`, or -1.

**Operative interval.** The store refuses a package whose sunset would fall before `_exp ≥ _due + 1`. A package's provisions start with `_since = now`, and rule 2 needs `_since < now`, so a package's own sunset can never run in its commencement call; every package is in force for at least one calendar month. The only same-call pair is the sunset of one enacted value followed by the commencement of a different package, in that order.

**Debug lines.** Each processor branch writes one `debug_log` line, `TE_TAX <branch> … month=<index> date=<game date> country=<name>`, with `<branch>` one of `dispatch` (global, date only), `process`, `skip`, `sunset`, `sunset_deferred`, `sunset_dropped`, `commenced`, `held_conflict`, `held_missed`, `watchdog`, `stored`, `store_refused`. `process` and `skip` are written for player countries only (every migrated country runs the processor monthly); every transition line is written for every country. The month comes from `[SCOPE.ScriptValue('te_history_month_index')|0]`, which printed `month=22032` from the tax probe's country event, and the date from `[TimeKeeper.GetCurrentDate.GetString]`, which vanilla 1.14.5's election lines print (for example "January 8, 2069").

### Storing a package

`te_tax_store_package = { SLOT = a|b }` (Task 6's pass calls it, after supersession) writes a package from the bill record if `te_tax_can_store_package = { SLOT }` (`common/scripted_triggers/te_tax_triggers.txt`) holds: the rule is on; the country has `te_tax_schema`; `te_tax_p<s>_on = 0`; `te_tax_bl_due` exists and is after the current month; and `te_tax_gen_bill_sunsets_valid`: every touched provision's offset `te_tax_bl_<key>_sun` is 0 (no sunset) or ≥ 1, which is `_exp ≥ _due + 1` for `_exp = _due + _sun`. Otherwise it logs `TE_TAX store_refused` and writes nothing.

- **Bill fields read** (Task 6 writes them; none is a schema token): `te_tax_bl_due`; `te_tax_bl_<key>`, `te_tax_bl_<key>_sun` (0, 6, 12, 24, 36 or 60), `te_tax_bl_xver_<key>`; `te_tax_bl_g_<good>`, `te_tax_bl_xver_goods`; `te_tax_bl_agrel`, `te_tax_bl_regrel`, `te_tax_bl_xver_relief`; the country state list `te_tax_bl_relief_states` (Task 11), read only if present.
- **Written** (`te_tax_gen_store_<s>`): every payload field. `_seq` = one above both slots' `_seq`. `_<key>_exp = due + sun` and `_<key>_succ` only for a touched provision with `sun ≥ 1`, else both -1. The successor is the value the provision will hold just before the due month: the enacted value, or the enacted `_succ` if the enacted sunset falls on or before the due month; overridden by the other slot's value when that slot is awaiting with an earlier due month and touches the provision, or by its `_succ` when its own sunset falls on or before the due month. A held other slot is ignored; if an earlier package is later held, the successor recorded here can be stale, which the review shows (Task 6).
- **Regional-relief states**: the slot's `te_tax_pending_relief_<s>` is cleared on every owned state; if `te_tax_bl_regrel ≥ 0` the package restates the state set (`_regrel_states_set = 1`) and each owned state in `te_tax_bl_relief_states` gets `te_tax_pending_relief_<s> = 1`; commencement moves the marks to `te_tax_relief_state` and clears them. A state that changes owner keeps its marks until the next store or commencement of that slot, so Task 10's `on_state_owner_change` clears `te_tax_pending_relief_a`/`_b` with `te_tax_relief_state`.
- `_state = 1` and `_on = 1` are written last, then `te_tax_recompute_next_month`. The store does not touch the enacted code or collection and does not record history: the pass records kind 6 (approved), and kind 8 (superseded) for the slot it supersedes.

### History

`te_tax_history_push = { KIND = <1..8> SLOT = a|b|none }` advances `te_tax_h_head` (1 to 8, then back to 1) and overwrites that entry with the month (`te_history_month_index`), the kind, the slot as `te_tax_slot_id_<SLOT>` and `te_tax_code_version`. Sunsets write through the generated `te_tax_gen_history_write = { KIND SLOT INST }` to record their instrument; every other caller uses the push, which records `_inst = 0`. The scheduler writes kinds 1 to 4; migration (Task 5) writes 5, the pass (Task 6) 6 and 8, the civil-war repair (Task 10) 7.

### Other entry points

`te_tax_apply_package = { SLOT }` applies a slot (only the processor's commencement uses it; it reads `te_tax_now`). `te_tax_recompute_next_month` refreshes the watchdog's cache.

### Scheduler retest (owner, in game)

The steps are in `docs/testing/tax-code-capability-ledger.md`, "Scheduler retest". Steps 2, 3, 5 and 6 need a stored package, which only Task 6's pass (or a debug command, not built) can create. Step 4 is `event te_tax.1` twice from the console in one month: the second logs `TE_TAX skip`.

## Files

| File | Holds |
|---|---|
| `common/scripted_effects/te_tax_state_effects.txt` | `te_tax_init_country`, `te_tax_copy_token` |
| `common/scripted_effects/te_tax_schedule_effects.txt` | `te_tax_process_month`, `te_tax_watchdog_month`, `te_tax_store_package`, `te_tax_apply_package`, `te_tax_recompute_next_month`, `te_tax_history_push` |
| `common/scripted_triggers/te_tax_triggers.txt` | the rule gates and `te_tax_can_store_package` |
| `common/on_actions/te_tax_on_actions.txt` | `te_tax_monthly_dispatch` (global `on_monthly_pulse`), `te_tax_watchdog_on_action` (`on_monthly_pulse_country`) |
| `events/te_tax_internal_events.txt` | hidden country events `te_tax.1` (processor) and `te_tax.2` (watchdog) |
| `common/scripted_effects/te_tax_collection_effects.txt` | `te_tax_sync_collection`, `te_tax_pick_sponsor`, `te_tax_sync_relief` |
| `common/scripted_effects/te_tax_generated_effects.txt` | generated: `te_tax_gen_sync_<key>`, `te_tax_gen_sync_goods`, `te_tax_gen_init_instruments`, `te_tax_gen_init_goods`, `te_tax_gen_init_schedule`; the scheduler's `te_tax_gen_sunset_<key>`, `te_tax_gen_commence_<s>`, `te_tax_gen_hold_missed_<s>`, `te_tax_gen_apply_<s>`, `te_tax_gen_store_<s>`, `te_tax_gen_next_month`, `te_tax_gen_history_write` |
| `common/scripted_triggers/te_tax_generated_triggers.txt` | generated: `te_tax_amendment_is_<key>`, `te_tax_amendment_matches_<key>` (amendment scope; the match reads `scope:te_tax_country`); `te_tax_gen_package_current_<s>`, `te_tax_gen_package_touches_goods_<s>`, `te_tax_gen_bill_sunsets_valid` (country scope) |
| `common/static_modifiers/te_tax_modifiers.txt` | `te_tax_relief_ag_1/2` (`building_group_bg_agriculture_tax_mult` −0.25/−0.5), `te_tax_relief_region_1/2` (`state_tax_collection_mult` −0.25/−0.5) |
| `common/script_values/te_tax_display_values.txt`, `te_tax_generated_values.txt` | display values above; `te_tax_slot_id_<s>` (generated) |
