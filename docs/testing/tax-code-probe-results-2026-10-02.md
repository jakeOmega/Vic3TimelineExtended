# Tax code probe results — 2026-10-02 UK first pass

**Tester:** Jake, repository owner. **Game:** Victoria 3 1.14.5.
**Initial mod revision:** `77da24c`. **Country:** UK / Great Britain.
**Other mods:** none. **Time:** about 30 minutes, plus targeted follow-ups.
No different revision was reported for the follow-ups. DLC and generated-doc provenance
were not supplied. Evidence is the tester's report, Budget/pop observations, and the
log excerpt below; no saves or full logs are attached.

Uses the [focused runbook](tax-code-probes.md) and informs the
[implementation plan](../superpowers/plans/2026-09-30-legislated-tax-code.md).
“Worked” means the stated qualitative behavior in this setup, not complete economic
reconciliation, every tax channel, or release validation. Follow-ups supersede the
initial interpretation that failure to collect implied a failed amendment carrier.

## Observations and decisions

| Check | Result and evidence | Implementation decision |
|---|---|---|
| R1a Territorial wage relief | Worked. London payer rate fell from 5% to 2.5%; a non-London payer stayed at 5%. Reported capital payer deduction before relief was £66; state receipts fell from £2.79k to £2.07k. Many building tax receipts fell about 50%; aggregate state receipts did not halve exactly. | Include demonstrated state wage relief. Other channels, selective exemptions, stacking, and remote-owner incidence remain unverified. |
| R1b Agricultural relief | Worked for wages: agricultural workers fell from 5% to 2.5%, while non-agricultural workers stayed at 5%. Failed to relieve the tested dividends: a Yorkshire Manor House aristocrat stayed at 5%; a Financial Center capitalist comparison also stayed at 5%. | Limit initial agricultural concessions to the demonstrated wage channel. Targeting ownership buildings is a new candidate, not verified agricultural dividend relief. |
| R2a Economic script observations | Worked for readable, responsive aggregates. Rough initial readings were 32.4k and −61.0k; after Wage 0.05, `tax_income` was 39.5k and balances −54.2k. UI wage receipts were 4.15k; the zero-bench aggregate resembled minting around 32.3k. The supplied log records `tax_income=32176.123` at stage 2 with no operative probe taxes. | Fiscal feedback is feasible; exact coverage is unresolved. Treat `tax_income` as an unclassified aggregate until its baseline/components and update timing are checked. Do not label it pure domestic tax receipts or infer a wage base from it. Minting inclusion is a hypothesis. |
| R2b Script-readable taxable bases | Unavailable in inspected docs. A bounded `triggers.log` search found no direct pre-tax pop wage/dividend/consumption getters. | Begin with explicitly approximate estimates and documented proxy/representative inputs; keep unsupported distribution claims absent. This is not proof of engine-wide impossibility. Building `earnings` is documented as annual earnings per employee; `earnings × level` is not a validated tax base. |
| R3 Amendment coexistence and collection | Worked on the targeted rerun. Manual commencement with `event te_debug_tax.62` in the due month entered stage 3; Budget and pop views showed both wage and dividend collection. | Retain the amendment carrier for the tested flat wage/dividend combination. This does not establish arbitrary clause counts or accounting atomicity during an automatic boundary transition. |
| R3 Reconstruction | Worked. The tester then ran `event te_debug_tax.65` twice: same taxes and dates, still unchanged after about one game week. | Use this mechanism as the starting collection writer; production reconstruction still needs version, migration, and lifecycle tests. |
| R3 Automatic scheduling | Failed for commencement in the initial run. Pending stage 2 persisted through due month 22033; at 22034 the log shows commencement immediately followed by expiry. Subsequent expiry was observed exactly at a month boundary. | Fix and retest dispatch/clock boundaries early. Cause remains unresolved; do not replace the carrier on this evidence. |
| R4 Country variables | Worked. Pending stage, Due 22033, and Expiry 22034 survived save/reload with original dates. | Start with bounded country-variable slots and absolute dates; approved future packages remain separate from the current debate slot. |
| R4 Containers | Partial. Two-record count survived reload and the third append was rejected. The inspector printed only `owned records=2`, not the nested owner/month fields. | Do not classify containers as broken. The existing inspector counts owner-matching records; a fresh inspection after reload supports reference/owner access, whereas a surviving cached count alone does not. Month-field persistence and independent copies remain unverified. Fixed slots are the initial simplification. |
| Customs / schools / native AI / civil-war storage | Skipped. | Verify competent customs authority and control of native AI fiscal writes early, before investing heavily in dependent integration. Check delivered school levels before offering service promises; choose and test civil-war copying/reunification during lifecycle work. |

## Scheduling evidence and narrow follow-up

The initial log contains this sequence (wall-clock timestamps, not game dates):

```text
12:22:55  month=22032 version=1 stage=2 operative=0 due=22033 expiry=22034
12:23:40  commenced both clauses
12:23:40  expired to explicit zero successor
12:23:40  month=22034 version=3 stage=5 operative=0 due=22033 expiry=0
```

The [tested queue](../../common/scripted_effects/te_debug_tax_effects.txt) has separate
commencement and expiry branches with `current_month >= deadline` checks. When processing
occurs at/after both deadlines, it can rebuild the taxes and then remove them in the same
call, giving the economy no collection interval. The log confirms both branches ran;
it does not identify why automatic commencement missed its due month. Manual commencement
subsequently demonstrated the carrier and actual collections independently of dispatch.

Investigate the [monthly hook](../../common/on_actions/te_debug_tax_on_actions.txt),
`te_tp_last_month < te_history_month_index` guard, and
[calendar index](../../common/script_values/te_history_values.txt) at event entry around
the due boundary. An operator/date boundary issue is a tester hypothesis, not a proven
cause; the deadline comparisons already use `>=`.

Retest automatic commencement and expiry with observations immediately before/at/after
the boundary and the first accounting updates; ensure the package has a real operative
interval. Keep duplicate processing idempotent. Deliberately late dispatch is a separate
case: define the production hold/rescheduling or catch-up policy explicitly instead of
silently calling a transient apply-and-remove a successful on-time commencement.

## Decision for implementation

Proceed with the core canonical schedule, amendment-backed flat wage/dividend collection,
demonstrated wage relief, bounded country-variable records, and explicit approximate
estimates. These results do not complete plan packages 0–1 or any production checkbox.

Automatic scheduling and aggregate-income semantics are immediate technical follow-ups.
Native AI fiscal interception and shared-market/treaty customs authority are early
integration investigations because they enforce the one-schedule/player-AI invariants.
Schools, additional channels, richer concessions, migration, conflicts/supersession,
both civil-war outcomes, AI solvency, UI coverage, balancing, and performance retain
their dependent implementation/release gates. No full extended-matrix rerun is required
to start supported work.
