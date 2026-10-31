# History Store and Charts

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

## History Store and Charts

A bounded, save-persistent store of monthly samples, plus a reusable column chart that renders them inside a journal entry. The banking system is its first consumer; the reserve and UN series are meant to be added with a sampling call and a chart instance and nothing else.

### Files

| File | Role |
|---|---|
| `common/script_values/te_history_values.txt` | the clock (`te_history_month_index`), the cap, eviction order, the "available since" readers |
| `common/scripted_triggers/te_history_triggers.txt` | `te_history_country_is_tracked` — the one eligibility rule |
| `common/scripted_effects/te_history_effects.txt` | generic country and global recording/pruning helpers |
| `common/scripted_effects/te_history_banking_effects.txt` | the banking series' sampling + marker wrappers |
| `common/scripted_effects/te_history_strategic_reserve_effects.txt` | the Strategic Reserve's per-good fill series (`st_res_<good>`, one per unlocked good), charted inside each good's expanded inventory row |
| `common/scripted_guis/te_history_scripted_gui.txt` | `te_history_marker_tooltip` — display-only, emits `custom_tooltip` lines |
| `gui/journal_entry_widgets/te_history_chart.gui` | the reusable `te_history_chart` / `te_history_bar_*` / `te_history_range_button` types |
| `gui/journal_entry_widgets/banking_history_widget.gui` | the three banking charts, wired to `custom_widget_container_2` of `je_banking_cycle` |

### Data model

**One script container per (country, month), not per metric.** Each container carries:

| Variable | Meaning |
|---|---|
| `te_hist_i` | monotonic month index (`te_history_month_index` = `year * 12 + month`, Jan = 0) |
| `te_hist_y` / `te_hist_mo` | calendar year and month 1–12, display only (the GUI has no integer division) |
| `te_hist_v_<METRIC>` | one per metric recorded that month |
| `te_hist_mk` | number of markers that month — its presence is what draws the marker pip |
| `te_hist_mk_<MARK>` | one per distinct marker recorded that month |

Tags are `te_hist te_hist_sample` (plus `te_hist_global` for the global series); the parent is the recording country, so the engine culls the history when the country stops existing. The country holds `te_hist` (the capped list), `te_hist_cur` / `te_hist_cur_i` (the current month's container and its index — the once-per-month guard), `te_hist_now_i`, and `te_hist_since_y` / `te_hist_since_mo`.

Sharing one container between all of a month's metrics is what makes the store affordable: 240 containers per tracked country covers *every* series rather than 240 per series, and a month's markers land on the same container as its readings, so the chart never has to search for them. A metric that was not recorded in a month simply has no `te_hist_v_<METRIC>` variable there — that is how the charts tell **missing data from a genuine zero**, and why a country that drops out of eligibility leaves a visible gap rather than a run of zeroes.

`te_history_month_index` is stateless: the same arithmetic on the current date, identical for every country and for the global series. Nothing has to be seeded on an existing save, two pulses in one month resolve to the same container, and there is no counter that can drift.

### Caps and eligibility

- **Cap:** `te_history_sample_cap = 240` — twenty years of monthly samples, defined once (also written as the literal `241` in both pruners). One sample is added per month and `te_history_prune_samples` evicts exactly one when the list goes over, using `ordered_in_list { position = 0 order_by = te_history_sample_order }` so the oldest goes regardless of how the engine orders the list. `te_history_sample_order` **negates** the month index, because Jomini's `ordered_*` iterators sort descending — ordering by the raw index would put the *newest* sample at position 0 and the pruner would destroy the container it had just created. (`un_resolution_age_order` negates for the same reason.) The evicted container is `destroy_container`ed after `remove_list_variable`, never before, so the list never holds a dead reference.
- **Re-sorting after eviction:** `remove_list_variable` fills the removed slot with the list's *last* element instead of shifting, so one eviction moves the newest sample to the front of the list — and the chart draws raw `GetList` order. Confirmed from a 1865 save: every store at the cap held `[the newest k months][the oldest 240 - k]`, one break, while every store still under the cap was chronological. `te_history_prune_samples` therefore calls **`te_history_sort_samples`** after each eviction, which rebuilds the list oldest-first. It builds the sorted copy into `te_hist_tmp` and clears `te_hist` only once that copy is provably complete (`count >= 240`, exact because the pruner runs at precisely the cap) — clearing first would strand 240 containers no list points at. `te_history_sort_global_samples` does the same for the global series. Check any save with `python3 scripts/analysis/check_save_history_order.py`. **A store that stops recording keeps whatever order it froze in** — the re-sort only runs on an eviction, and a country that has dropped out of eligibility never evicts again. That is unreachable rather than broken: the charts live on that country's own journal entry, and the first month it records again puts the list over the cap, which evicts, which sorts. The checker labels those `frozen` and does not fail on them.
- **Eligibility:** `te_history_country_is_tracked` = `is_player = yes` OR `country_rank >= rank_value:major_power`. Identical for AI and human countries. `unrecognized_major_power` (rank_value 5) is deliberately out — those countries are numerous and rarely run the charted systems.
- **Dropping out:** a country that falls below the bar stops sampling and **keeps** its stored history; nothing prunes it early. It is bounded at 240 containers and dies with the country, so stale history costs at most one country's worth of samples. Re-entry resumes recording and the gap renders empty.
- **System gating:** a series also gates on its own system. `te_history_record_banking_samples` requires `te_banking_system_on = yes` and `has_journal_entry = je_banking_cycle`, so a country with banking switched off records no banking metrics at all. Under `banking_system_simplified` the three cycle series and the two rate series are still sampled; `mon_inflation` and `mon_fx` are not (they would flatline), and their two charts are hidden on the same trigger.

### Markers

`te_history_record_marker = { MARK = <key> }` sets `te_hist_mk_<key>` on the month's container and bumps `te_hist_mk`. The banking markers are recorded at the single shared site each policy already has — the `banking_effect_<button>` helpers, which both the AI's journal-entry buttons and the dashboard call — plus `banking_cycle_check_and_execute_crash` (`crash`) and `banking_contagion_crash_check` (`crash_contagion`).

The tooltip is built in script, not in `.gui`: `te_history_marker_tooltip` is a `scope = country` scripted GUI with `saved_scopes = { te_hist_sample }` whose effect is nothing but `custom_tooltip` lines, rendered from loc with `[GetScriptedGui('te_history_marker_tooltip').ExecuteTooltip( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'te_hist_sample', ScriptContainer.MakeScope ).End )]`. Its policy branches print the policy's name, one line under "adopted" or "withdrawn" (GUI audit BNK-4, 2026-10-27). They used to quote the dashboard's whole `banking_dash_tt_<button>` tooltip, which put today's Requires line and live figures under a bar from years ago, and five of those keys read `JournalEntry`, which a bar's tooltip does not have. A verb-named button is named by its modifier ("Bank Holiday"). The three cycle charts' bars name that month's band (phase, momentum band, bubble band) with an `AddLocalizationIf` chain over the stored reading; `test_banking_layout.HistoryBandTest` holds the chains to the overview's words. `is_valid`/`ai_is_valid` are `always = no`, so neither a player nor the AI can ever execute it.

### Opening the GUI never writes state

Every recording helper body is wrapped in `hidden_effect`. That matters because the `banking_effect_<button>` helpers are also rendered as button tooltips; during a tooltip render the engine resolves scope links but never creates containers, so an unwrapped call would both spray text into the policy tooltip and read a scope that was never set. The chart itself has no effect at all: the only click targets are the collapse header and the three range buttons, and both write GUI-variable-system values that never reach the save.

### The chart

`plotline` cannot be used. Its `plotpoints` property only accepts the output of `GetTrendPlotPoints` / `GetTrendPlotPointsNormalized` / `GetDynTrendPlotPoints`, all of which take an engine-side `DataTrend`; no global function in the 1.14 data-type docs returns a `DataTrend`, and no `DataTrend` exists for a mod variable. So the chart is one vertical `progressbar` per stored month, over `datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('te_hist')]"`.

- **Width.** The plot is a fixed-width `hbox`; each item is `size = { 0 84 }` + `layoutpolicy_horizontal = expanding` and no maximum width, so the *visible* bars divide the width between them (vanilla's `levels_progressbar` idiom). Switching to 1 year widens the bars instead of leaving 228 empty slots. At the 20-year end the 480px plot is split 240 ways — 2px a bar, so the series reads as a shape, not as countable months. An out-of-range item pays for its `visible` test and nothing below it, so the short ranges stay as cheap as they were before the cap doubled.
- **480 is not a round number, it is a divisible one.** Bar widths are integer pixels, and whatever the division leaves over the layout hands to the last item, i.e. to the newest month. 480 divides all three full-store bar counts exactly (240 / 60 / 12 → 2 / 8 / 40px), so no range leaves a remainder. The plot was 484px until #366, which is 4px over in all three cases: the newest month drew 6px against every other month's 2px on the 20-year view, three times as wide as its neighbour, and 12px against 8px on the 5-year one. Changing the plot width or adding a range means re-checking that `plot_width % bar_count == 0` for every range. A chart whose full ranges come to another width sizes its frame to them with the optional `plot_size` block (the 496px default is 480 + the plots' 8px right margin + 8). Cultural Hegemony's annual chart draws 5 / 20 / 100 years at 80 / 20 / 4px, 400px in all, in a 456 × 180 frame: a 48px column for its axis labels, then the bars to the right margin. Left at 496 it showed ~90px of empty frame on the left of a full 100 years. `test_cultural_hegemony_history.test_full_ranges_fill_the_frame` checks the arithmetic.
- **Ranges.** `GetVariableSystem` holds `te_hist_range` = `1`, `5` or `20`; unset means 20 years, which is the whole store, so the default view needs no per-bar test to pass. Each bar's `visible` compares `te_history_month_index` (now) minus its own `te_hist_i` against 12 / 60.
- **Signed series.** `te_history_bar_signed` stacks two half-height bars around a zero axis. The lower one uses vanilla's `double_direction_progressbar` "REVERSE HACK": swap `progresstexture` and `noprogresstexture` and give the bar a `min .. 0` range, so the coloured part is drawn from the far end and hangs down from the axis. Both halves clamp their value with `Max_CFixedPoint`/`Min_CFixedPoint`, so a positive month draws nothing below the axis and vice versa.
- **Two signed series deliberately do *not* use it** — the digital-currency policy-rate chart (−3…12) and the inflation chart (−4…12). `te_history_bar_signed` splits the plot 50/50 whatever its two ranges are, so on an asymmetric range a −2% month draws taller than a +2% one: a scale discontinuity at exactly the line those charts exist to watch. Both instead use `te_history_bar_unsigned` over **one linear span** with a manually drawn 0% line (a `zero_axis` blockoverride positioned from the plot margin plus the zero fraction of the plot height), and one colour above and below it — `te_history_bar_signed`'s green/red split would say deflation is the opposite of a problem. The offsets (23px and 27px) cannot be checked from the files; both are on the in-game checklist. If a new series is signed and its range is asymmetric, copy the inflation chart, not the momentum one.
- **Banded colour.** One chart does not use `te_history_bar_unsigned`: the banking cycle-value column is `te_history_bar_cycle_phase` (declared in `banking_history_widget.gui`, its only consumer), which draws the month in the colour of the phase its reading falls in. A progressbar's `color` *can* be an expression, but the only way to produce a `CVector4f` is `Select_CVector4f` over two colours that already exist as engine getters, and there is no `CVector4f` literal to nest into it — so the six colours are six progressbars in the same slot, each `visible` only inside its band, over one shared dark cover. Bands are the phase ladder from `banking_cycle_effects.txt` (10 / 25 / 40 / 60 / 75 / 88); the RGB values are vanilla's named text colours from `gui/textformatting.gui`, so a bar is literally the colour the phase's name is printed in.
- **Marker key.** `te_history_marker_legend` (in `te_history_chart.gui`) is a two-row key for the pips: the `information.dds` pip, drawn on any month with a marker, and the `warning.dds` pip, drawn on a crash. The crash row is a `block` with a default body, so a series that never records a crash overrides `"crash_marker"` to nothing.
- **Empty state.** `IsDataModelEmpty` on the same list shows "nothing recorded yet" — what an existing save sees until its first monthly pulse. `te_hist_since` prints the oldest retained sample's date.
- **Collapsed by default.** The section header toggles a GUI flag named for the *open* state (the inverse of the dashboard's collapsed flags), so a player who never opens it never pays for the bars.

### How to add a series

1. **Sample it.** From the system's own monthly pulse, in country scope:
   `te_history_record_sample = { METRIC = res_stock VALUE = var:st_res_stock_grain }`
   Wrap it in the system's own gate (game rule + journal entry) the way `te_history_record_banking_samples` does. For a world-level series use `te_history_record_global_sample` instead; it writes to the global list and needs no eligibility trigger.
2. **Chart it.** Instantiate `te_history_chart` with blockoverrides for `chart_title`, `chart_legend`, `bar_tooltip` and `bar_body`. Use `te_history_bar_unsigned` for a one-sided metric (override `values` with `min`/`max`/`value` and `color`), `te_history_bar_signed` plus a `zero_axis` override for a signed one whose range is **symmetric** — for an asymmetric signed range use `te_history_bar_unsigned` over the whole span with a drawn zero line instead (see the two exceptions under **The chart** above). The bar body's `visible` must be `[ScriptContainer.HasVariable( 'te_hist_v_<METRIC>' )]` so months without that metric stay empty.
3. **Localize it.** A title, a legend, a `…_row` line and a tooltip key modelled on `te_hist_tt_bank_value` — the tooltip key is where the date line and the marker block are composed.
4. **Mark it, if the series has turning points.** `te_history_record_marker = { MARK = <key> }` at the single site the event already has, plus one branch in `te_history_marker_tooltip`.
5. **If it has no markers of its own, hide the pips.** Markers live on the month's shared sample container, so every chart of a country's store draws every system's pips (the banking policy "i" and crash "!" icons). A series whose tooltip does not explain them should add `blockoverride "marker_pips" {}` to its `te_history_chart` instance. The UN authority, global-warming and colonial charts do; the banking charts, which record and explain their own markers, do not. Cultural Hegemony now uses its separate annual model history without markers.

Nothing else. The store, pruning, ranges, marker pips, empty state and "available since" line are all shared. **Do not** add a second store, a per-metric container list, or a parallel chart implementation.

### Cost

Per tracked country: 120 containers, each with 3 bookkeeping variables plus one per recorded metric (3 for banking today), plus 6 country variables. The Strategic Reserve adds up to eight metrics (one per unlocked good) for a tracked country with a reserve, so its containers carry up to eight more variables each; the reserve adds no containers. Per month per tracked country: one container create, one destroy, ~6 `set_variable`, and two 120-element ordered scans. GUI cost is paid only while the section is open: 120 items per chart, each running one script-value evaluation for the range test.
