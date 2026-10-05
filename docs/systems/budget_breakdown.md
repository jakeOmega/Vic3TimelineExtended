# Budget Breakdown

The Budget panel's sixth tab, **Breakdown**, is available under every rule
setting. It reads the weekly income forecast and expense total from Overview,
then subtracts Investment Pool Transfer from both totals and from Construction
Goods. These are public-budget totals: private construction funding is excluded
from income, expenses, residuals and chart denominators. Each side has a pie and
an expandable list with currency amounts and percentages, sorted largest amount
first within each level. Groups start collapsed. Zero leaves and entirely empty
groups are hidden; groups with offsetting nonzero components remain expandable.
Negative adjustments remain in the list and are excluded from the positive
chart denominator. The headers are
the signed public-budget totals. Other Income/Expenses reconcile uncategorized and
temporary flows to those public totals.

## Expandable groups and pies

Income groups Taxes (including war-profit tax receipts) and Diplomatic Income.
Expenses group Administration (institutions plus General Administration),
Military, Shipping and Connections, Programme Costs and Diplomatic Payments.
Military expands into Army, Navy and Other Military Costs; Army and Navy each
expand again into Wages plus Materials and Support. Shipping separates
supply-ship construction, maintenance and port connections. Every original accounting
category occurs exactly once in the tree, except Military and Shipping whose
existing totals are subdivided into new leaves.

Branch wages are the engine's predicted branch total minus its goods expense.
The native branch getters can omit logistics-centre and naval-fortification
upkeep even though the main military goods total includes it. Read support
building deficits once using `every_scope_building`, selecting only Army
Logistics Centers for Army, and Naval Logistics Centers plus Naval Fortifications
for Navy. Barracks, conscription centers and Naval Administration are excluded:
the native branch amounts already cover their costs. Private industry and other
government buildings are also excluded. Nonnegative profits contribute zero.

Materials and Support = native branch goods + full support-building deficit.
Navy also adds warship construction and maintenance. Support combines its own
wages, goods and any slave upkeep; scripts cannot read those components
separately, so the label and tooltip identify the combined amount. Do not
subtract the native branch forecast from the support deficit: barracks unit
wages can be charged separately without appearing in building `weekly_profit`.
An all-branch building sum therefore cannot safely replace the native totals.

For example, £18,600 of barracks wages plus £29,800 of Army logistics goods and
£1,060 of logistics wages gives Army £49,460: Wages £18,600 and Materials and
Support £30,860. Subtracting barracks wages from that support balance would show
only £12,260 of support and leave an artificial £18,600 in Other Military Costs.
The regression fixture reproduces this case with zero barracks `weekly_profit`,
matching separate unit-wage accounting rather than assuming a building deficit
contains the branch's wages.

Weekly support balances can still differ from budget forecasts, so Other Military
Costs remains a signed reconciliation of the original total against Army plus
Navy. Supply-ship costs stay in Shipping; military-ship costs go to Navy once.
The original military total and both public headers retain their prior formulas.

A collapsed group contributes one slice; expanding it replaces that slice with
its visible descendants. Pie weights sum positive **terminal** leaf amounts,
so the denominator never changes during expansion. Group percentages sum their
children's percentages; their signed monetary totals can differ from that
positive sum when costs and refunds offset. A zero-net group can therefore have
a positive slice and expandable nonzero components. Hidden descendants retain
their GUI-local expansion flags; collapsing an ancestor hides every descendant
slice, including descendants previously expanded.

## Journal systems and source amounts

Banking, Covert Actions, Cultural Hegemony, Colonial Development, the United
Nations, Nuclear Program, Nuclear Civil Defence, Space Race and Drug Shortage
Response each have a separate expense category. UN grants, Strategic Reserve
sales, war-profit taxes and spectrum auctions have separate income categories.
Hover a row for the engine's applied modifier sources and amounts.

Each contributing static modifier has a `script_only` accounting field with
the same coefficient as its native `country_expenses_add` or
`country_tax_income_add`. The engine applies the same multiplier, stacking,
duration and decay to both fields. These fields have no economic effect. Their
localized descriptions clarify that the value is already charged/credited;
they also appear in the source modifier's ordinary tooltip. The panel reads
their current sums, then subtracts them from Additional Expenses/Income once.
Only the unattributed remainder appears in Other Additional Expenses/Income.
No live formula is reevaluated to guess what a timed modifier currently charges.

Only money in the weekly budget is included. One-time `add_treasury` payments
and costs in innovation, influence or other resources are excluded. For example,
Space Race's recurring `sr_space_program_cost` spends innovation, not money;
its monetary debris-clearance response is attributed to Space Race.

## Administration allocation

Only `building_government_administration` enters the administration pool.
Its negative `weekly_profit` supplies its operating cost: its production methods
produce bureaucracy and tax capacity, not saleable goods. This includes wages,
goods and any slave upkeep. Other government buildings remain in Other Civil
Buildings. The actual administration cost is capped at the Overview's civil
wage/goods/slave total because wages there are predicted while the building's
balance is from the latest week.

Let A be that administration cost, B be `produced_bureaucracy`, U be
`Country.GetInstitutionInvestmentBureaucracyCost`, and L the sum of current
institution investments. When B and L are positive:

- institution pool = min(A, A × max(U, 0) / B)
- institution i = pool × current investment i / L
- General Administration = A − sum(all institution allocations)
- Other Civil Buildings = Overview civil expenses − A

When B or L is zero the institution pool is zero. Using the sum of allocations
for the remainder also conserves currency after fixed-point truncation.
Institution-specific bureaucracy discounts affect U but deliberately do not
change the level-based split. Target levels awaiting implementation do not count.

With A = £39,000, B = 2,800, U = 1,400, Education level 3 and National Bank
level 2, the pool is £19,500: Education £11,700, National Bank £7,800 and
General Administration £19,500.

## Files and regeneration

`scripts/generators/gen_budget_breakdown.py` contains the income/expense
catalogue and discovers every institution from the committed vanilla snapshot
and mod definitions. Run it explicitly after editing the catalogue or adding an
institution. It writes `te_budget_generated_values.txt`,
`te_budget_generated_charts.gui`, `te_budget_generated_types.txt` and
`te_budget_l_english.yml`. Localization's
organizer preserves the generated BUDGET category. Hand-written calculation
rules are in `common/script_values/te_budget_values.txt`; the panel layout is in
`gui/te_budget_breakdown.gui`.

Each section binds the engine getters into a `TopScope`. The administration
building sum, military support-building deficits, total institution levels,
allocated pool and positive chart total are passed as value scopes before the charts are drawn, so nested cumulative
values do not scan buildings or repeatedly recalculate the whole denominator.
There are no effects, saved variables, pulse hooks or journal-entry dependencies.

The list binds every signed amount once, then caches each subtree's visible row
count. Each row's display rank counts preceding sibling subtrees at every
ancestor level and adds the ancestor headers. Amounts sort descending; catalogue
order breaks ties. This produces the same order as a sorted preorder traversal.
One flat set of normal flow slots selects rows by cached rank and visibility,
avoiding nested slot grids that multiply widget instances. Zero and hidden rows
consume no space. The engine determines list height and positions; expressions
inside brace-vector components are unsupported and collapse rows onto each
other. Rows have a 28-pixel minimum and grow for wrapped labels, with indentation
at each level. Expansion flags live only in `GetVariableSystem`, never saves.

The palette stays in catalogue order so sorting never changes category colors.

Historical stacked bars are deferred: script pulses expose aggregate budget
values but not the GUI getters needed for exact monthly category snapshots.
Recording only when Breakdown is open would leave gaps and miss closed-tab
months. The horizontal current-week bar has been removed.

The palette reuses Cultural Hegemony's existing pie textures and colors; it
repeats with many institutions, so category names and percentages remain visible.

## Validation and in-game checks

`test_budget_breakdown.py` executes the actual script values in a strict offline
harness: the requested example, shortages, zero production, absent and zero-level
institutions, current-level changes, reduced civil wages, negative adjustments,
tied row amounts, zero rows, category reconciliation, military branch accounting
and modern support buildings, every combination of expansion flags, sorted preorder ranks, zero-net groups,
cumulative pie layers and private-spending exclusion. GUI lint and reference audits cover local names, localization, braces and textures.
Source tests also verify separate simultaneous JE charges, signed banking
offsets, exact mirror coefficients, complete attribution of the mod's recurring
monetary sources, and unchanged economic fields.

Engine rendering and accounting still require an in-game check:

1. Open Breakdown with banking/tax rules both disabled, then enabled. Check all
   six tabs fit, zero rows disappear, long institution names wrap and tooltips
   retain the parent `TopScope` context. Check sorted flow slots and list
   height after a tax change: rows must move without overlap or gaps, with equal
   amounts in catalogue order and negative adjustments below positive amounts.
2. Compare administration's `weekly_profit` against the sum of those buildings'
   wages and goods, including a construction-good input under FMC. Confirm that
   treasury funding does not turn that profit into zero.
3. Compare all list amounts and public totals with Overview minus Investment Pool
   Transfer after a weekly tick, a wage change,
   institution investment completing and an administration building changing PM.
4. Check pie colors/shares match the sorted list; no-production and zero-
   budget countries have empty charts. Test a bureaucracy shortage and a country
   with an institution-specific bureaucracy discount.
5. Open the panel in a large country and check frame time. All intermediate
   GUI bindings must refresh with current values while sharing them with children.
6. Expand every group and nested Army/Navy, then collapse Military while Army
   remains open. Check pies show exactly the visible frontier and restore the
   child expansion state on reopening. Confirm totals and denominators stay
   unchanged, including an offsetting Programme Costs refund. Check arrows,
   indentation, wrapped labels and frame time with Administration expanded.
7. Compare modern military upkeep against Overview's building-type tooltip.
   Army logistics must appear in Army's Materials and Support; naval logistics
   and fortifications must appear in Navy's. Check an empty branch, conscription,
   a wage change and slave upkeep. Confirm native barracks/conscript/Naval Administration costs are not added
   twice or deducted from support upkeep, and public totals remain unchanged.
8. Apply Banking and Covert Actions charges together. Check their rows and source
   tooltips against Additional Expenses, including JE-owned modifiers, decaying
   charges, refunds and removal. On an existing save, verify modifier-definition
   changes are picked up; otherwise let the owning system refresh its modifier.
