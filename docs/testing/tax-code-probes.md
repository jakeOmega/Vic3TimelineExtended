# Tax code probes — architecture risks before implementation

**Goal: find engine limitations that would change the tax system we build.**
The [design](../superpowers/specs/2026-09-29-legislated-tax-code-design.md) needs
payer-backed concessions, useful economic observations, multiple operative clauses,
and records for approved future changes. Those are the first questions below.

Applying a vanilla wage tax, disabling a Budget button, and saving an ordinary applied
tax are smoke tests; they do not answer these questions. GUI controls can be edited or
removed. Custom record references and dates, however, deserve a targeted reload check.

Use one suitable country and a disposable save. Aim for a **20–30 minute first pass**;
report partial results when time runs out. No scenario collection, repeated control runs,
national reconciliation, hardware inventory, or mandatory attachments. A skipped risk
remains unresolved for the implementation that depends on it; elapsed time is not a pass.
Use the [short results form](tax-code-probe-results.md), one observation and decision per row.

## Setup

Use the current mod containing the PR #585 harness, without a duplicate Workshop copy.
Restart in debug mode and load a **copy** of a quiet save with an incorporated capital,
another incorporated state, employed wage earners, and preferably profitable private
agriculture. Keep the original untouched: **Zero carrier replaces the taxation law**.
Clear bench and Disarm do not restore it; reload the original after testing.

Pause, run `event te_debug_tax.1`, and open **Timeline Extended → Tax Probes**.
If the tab fails, use the console commands below. Stop on a crash or script error and
record the affected step; do not spend the session troubleshooting.

Click **Zero carrier** (`event te_debug_tax.3`), advance about a week, and pause.
Confirm the effective domestic rates are zero, noting any residual contributors from
other laws/modifiers. Save this as the **zero bench**. Reload it between independent
treatments: rate buttons clear other probe tax amendments, but retain relief modifiers.
Zero carrier does not remove taxed-goods selections, tariffs, or modifiers on other laws.

For economic observations, compare the same identified pop/state and income source
after roughly one weekly accounting update. Note rates, payer deductions, and relevant
receipts; rough figures suffice. A modifier icon or changed rate label alone is insufficient.
Mark a noisy or missing comparison unclear instead of chasing exact percentages.

## R1. Do territorial and sector concessions benefit the intended payers?

**Risk:** `state_tax_collection_mult` might reduce collections without reducing household
liability, and a building-group tax multiplier might affect a different channel or owner
than its name suggests. This determines which concessions can actually buy political support.
Existing harness: extended P06.

1. From the zero bench, click **Wage 0.05** (`event te_debug_tax.10`), settle, and note
   wage deductions for a capital pop and a noncapital pop, plus capital tax receipts.
2. Click **State Relief** (`event te_debug_tax.20`, capital collection multiplier −50%).
   Settle and compare the same payers and receipts. Does the capital payer save money?
   Is the noncapital payer unaffected? Keep any income changes visible.
3. Reload the zero bench. Use **Dividend 0.05** (`event te_debug_tax.11`) if a pop has
   identifiable dividends from profitable agriculture; otherwise use Wage 0.05 with an
   agricultural worker and record that narrower coverage. Note that payer and a
   manufacturing comparison, then apply **Agriculture** (`event te_debug_tax.24`, −50%).
   Settle and identify who, if anyone, saves tax. If an owner lives outside the producing
   state, note where they live; do not assume the building's location selects the taxpayer.

**Decision:** offer only the demonstrated scope/channel as relief. If receipts fall while
payer deductions do not, this is a collection loss, not a taxpayer concession. If sector
relief has no demonstrated beneficiary, omit it initially. One wage test does not establish
dividend, consumption, selective-instrument, or remote-owner exemptions. Test those only
before adding the corresponding concession; broad relief is an acceptable reduced scope.

## R2. Can simulation scripts read the inputs estimates and AI need?

**Risk:** a number visible in Budget or a pop tooltip may have no simulation-script getter.
Receipt totals are not taxable bases, especially when the current rate is zero.
Existing harness: extended P00/P18.

1. Reload the zero bench and click **Snapshot** (`event te_debug_tax.2`). Record
   **Script receipts**, **Fixed balance**, and **Total balance** against the corresponding
   Budget figures. Script receipts come from `tax_income`: all domestic taxes, excluding
   tariffs and external transfers. Compare matching totals, not only the wage row.
2. Apply Wage 0.05, advance a week, pause, and Snapshot again. Do the stored script values
   respond plausibly? Read `te_tp_obs_tax_income`, `te_tp_obs_net_fixed_income`, and
   `te_tp_obs_net_total_income` in country variables or `TE_TAX_PROBE` log lines if needed.
   **Live GUI wage/head receipts** use GUI getters and do not establish script access.
3. **Developer check before choosing the estimation model:** inspect the installed build's
   generated trigger/value documentation for pre-tax wage/dividend/consumption bases,
   payer deductions, and useful state/sector/pop breakdowns. Record each exact getter,
   scope, units, and coverage. For any candidate, evaluate it into a temporary snapshot
   variable at zero and nonzero rates and compare with the same pop/state in game.
   A documentation entry is only a candidate. The existing harness has no taxable-base
   reader, so this step cannot be passed by pressing Snapshot or viewing a tooltip.
   If no suitable candidate is found in a bounded source inspection, record
   **unavailable in inspected docs**, not proven impossible in every engine version.

**Decision:** aggregate receipts/balances support fiscal feedback but cannot establish
an exact new-tax forecast or household incidence. If bases are unavailable or still untested,
start with explicitly approximate estimates and documented representative/proxy inputs;
keep unsupported distribution claims absent. Dividing zero receipts by a zero rate provides
no base. Do not temporarily enact a draft just to measure it. Choose this fallback before
building the preview and AI around unavailable data.

## R3. Can independent clauses coexist and rebuild without losing or doubling taxes?

**Risk:** native amendment exclusivity/cardinality or application timing could invalidate
a multi-clause code even though a single tax works. Ordinary lifecycle bookkeeping is
implementation work; this small combination test establishes the collection mechanism.
Existing harness: extended P07/P13.

1. Reload the zero bench. Click **Draft two clauses** (`event te_debug_tax.60`) then
   **Approve draft** (`event te_debug_tax.61`). These propose wage 5% plus dividend 5%.
   Approval is a developer stand-in. Stage should be 2; rates/collections remain unchanged.
   Note the displayed **Due** and **Expiry** absolute month indices.
2. Complete R4's record/reload check now, using this pending package.
3. Advance to the first country monthly pulse in the due month. Check stage 3 and
   **both** wage/dividend amendments and effective 5% rates. Observe the first daily and
   weekly updates: identifiable wage and dividend payers should pay once in their channels,
   without a missing or doubled collection interval. If there is no dividend-paying pop,
   record the rate coexistence separately and leave dividend economics unclear.
4. Click **Rebuild operative** (`event te_debug_tax.65`) twice. Both clauses should remain
   5%; no accumulation to 10%, missing clause, or changed due/expiry dates. Advance to the
   expiry month: stage 5 and both rates return to their explicit zero successor.

**Decision:** use amendments only for the combinations demonstrated. If they cannot coexist,
investigate a static-modifier/canonical-variable carrier (extended P07) before writing the
production collection layer; do not split legislation into unrelated free toggles. Monthly
scheduling is the harness candidate, not proof of day-precise dates or multiple queued bills.
Conflict/supersession algorithms get their own implementation tests later.

## R4. Are custom records usable, owned, and persistent?

**Risk:** lists of scripted containers holding country references and absolute dates are
less established than vanilla's saved tax settings. This chooses the bill/obligation
representation. Run during R3 so it costs only one reload. Existing harness: extended P12.

1. While R3's package is pending, click **Append record** (`event te_debug_tax.67`) twice,
   then **Inspect records** (`event te_debug_tax.68`). Owned count should be 2.
2. Append a third time. Expect the log's **capacity two** rejection and two unchanged
   existing records, not silent replacement. Inspect `te_tp_records` and its containers:
   each has `te_tp_record_owner` pointing to this country and `te_tp_record_month`.
   Count alone cannot verify the references or fields.
3. Save to a throwaway slot, reload once, Inspect records and Snapshot. Check both
   references/owners/month fields, stage 2, and the **original** Due/Expiry values.
   Resume R3 and check that commencement and expiry use those dates.

**Decision:** if container storage fails, use a bounded set of country-variable slots and
absolute dates, then test that representation before committing to it. A successful count
does not prove arbitrary nested objects or revolution inheritance. Fixed slots can still
record approved future bills separately from the active debate; do not make pending
commencement block all subsequent legislation.

## Targeted checks before adding the corresponding feature

These are high-risk dependencies, not a request to run the extended matrix. Run only the
selected feature's check before implementing it. Record missing setup as skipped.

| Feature / risk | Small discriminating check | Implementation decision |
|---|---|---|
| Customs: do goods/direction modifiers affect actual duties, and who has authority? | On an untouched native trade-policy bench with active grain trade, note grain and another good, both directions, selected levels, effective rates, receipts/subsidy expense, and market owner. Set grain import low (`event te_debug_tax.41`), then Grain Import (+0.10, `event te_debug_tax.29`); exports and the other good are comparisons. Reload; repeat export low (`event te_debug_tax.46`) plus Grain Export (`event te_debug_tax.30`). Before shared-market/treaty integration, compare native UI and the direct setter as a member or under a no-tariffs constraint (extended P08–P10). | Distinguish selected level from effective rate and subsidy costs. A direct setter may bypass legality; it does not establish authority. Add explicit validation where observable. Defer unsupported overrides/partner preferences; keep customs experimental if competent authority cannot be enforced. |
| Service bargains: is the school observation a delivered level or a requested target? | On the untouched original with schools, arm and Snapshot, request one normal institution expansion, then Snapshot while expansion is incomplete. Compare `te_tp_school_level` and `te_tp_school_expanding` against requested/delivered UI values. Continue to completion only if the early reading is ambiguous (extended P16). | If the trigger reports the target early, it cannot alone verify delivery. Use a verified completion/actual-level source or omit delivery promises; never reward an undelivered service. |
| Native AI: can automatic fiscal writes be prevented independently of the GUI? | Before integrating AI countries, inspect the installed native AI mutation paths; on one disposable AI country, arm the carrier and observe law, levels, goods and amendments during a fiscal-stress interval. The harness's UI lock leaves native AI/script setters unblocked. Use extended P07/P11/P14 for a targeted intervention and rerun. | A changed setting exposes a path to intercept. No change during a short run proves nothing about prevention. Patch exposed paths and establish a workable control before claiming one authoritative AI schedule; a later periodic reset can hide an illegal interim change. |
| Civil wars: are records copied, shared, or merged from the loser? | Before choosing a copy/reunification strategy, use an existing near-uprising save with an operative/pending package and two records. Inspect original/target raw fields at outbreak (`event te_debug_tax.91`); do not arm/rebuild the target first. Check owner references and dates (extended P15). Both victory outcomes belong to later lifecycle validation. | Missing inheritance calls for explicit copying. Shared containers require independent records; loser-only merges require ownership/version cleanup. Failure of automatic inheritance is not failure of the tax idea. |

## Granularity and exit rule

The current native hooks and harness cover **flat** wage/dividend rates, rural/head
monetary assessments, and selected consumption goods at **one common rate**. They do not
establish marginal brackets, allowances, separate domestic rates per good, wealth,
inheritance, corporate-profit, land-value taxes, or bilateral tariff preferences.
Before exposing any of these, identify a real base, payer deduction, and collection hook
and run one targeted economic experiment; otherwise omit it or choose the design's
honestly named fallback. The global Consumption High button cannot test per-good rates.

At the end, record **worked / failed / unclear / skipped**, the demonstrated scope,
and the architecture or catalog decision. Begin production work on supported mechanisms
or explicit reduced scope. Resolve a failed/unknown dependency before building the part
that relies on it; unrelated work can continue.

Reload the original before normal play. The [extended runbook](tax-code-probes-extended.md)
and [extended form](tax-code-probe-results-extended.md) preserve detailed follow-ups,
the command appendix, and removal instructions. They are optional references, not an
all-at-once prerequisite. Full migration, menu coverage, conflict cases, AI solvency,
both civil-war outcomes, balancing, and performance remain implementation/release
validation. Basic loading, Budget locks, and ordinary tax reloads are smoke/regression
checks if those surfaces change, not the main pre-build feasibility evidence.
