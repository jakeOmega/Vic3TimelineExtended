# Legislated tax code: canonical state and the collection writer

The variable schema of the legislated tax code (spec: `docs/superpowers/specs/2026-09-29-legislated-tax-code-design.md`; plan: `docs/superpowers/plans/2026-10-02-legislated-tax-code-tasks.md`), the one effect that turns it into native tax settings, and the display values that read it. Later tasks extend the schema table and the sections below; `test_tax_code_state.py` parses the table and checks it against the initialiser.

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

## Initialisation

`te_tax_init_country` (country scope, `common/scripted_effects/te_tax_state_effects.txt`) writes every country row above that is absent, with its sentinel, and never touches one that exists. The per-instrument and per-good rows come from the generated `te_tax_gen_init_instruments` and `te_tax_gen_init_goods` (`common/scripted_effects/te_tax_generated_effects.txt`). `te_tax_schema = 1` is written last, so a country holding `te_tax_schema` holds every token of that schema version. Each write has the shape `if = { limit = { NOT = { has_variable = X } } set_variable = { name = X value = <sentinel> } }`, which `je_immediate_reset_audit` accepts if a journal entry's `immediate` ever calls it. The state variable `te_tax_relief_state` is not initialised: a state without it is named in no relief.

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

## Files

| File | Holds |
|---|---|
| `common/scripted_effects/te_tax_state_effects.txt` | `te_tax_init_country`, `te_tax_copy_token` |
| `common/scripted_effects/te_tax_collection_effects.txt` | `te_tax_sync_collection`, `te_tax_pick_sponsor`, `te_tax_sync_relief` |
| `common/scripted_effects/te_tax_generated_effects.txt` | generated: `te_tax_gen_sync_<key>`, `te_tax_gen_sync_goods`, `te_tax_gen_init_instruments`, `te_tax_gen_init_goods` |
| `common/scripted_triggers/te_tax_generated_triggers.txt` | generated: `te_tax_amendment_is_<key>`, `te_tax_amendment_matches_<key>` (amendment scope; the match reads `scope:te_tax_country`) |
| `common/static_modifiers/te_tax_modifiers.txt` | `te_tax_relief_ag_1/2` (`building_group_bg_agriculture_tax_mult` −0.25/−0.5), `te_tax_relief_region_1/2` (`state_tax_collection_mult` −0.25/−0.5) |
| `common/script_values/te_tax_display_values.txt`, `te_tax_generated_values.txt` | display values above |
