# Tax code probe results — extended investigation

**Optional reference, not the first-run form.** Use the [short form](tax-code-probe-results.md)
for architecture risks. For a selected follow-up, fill only relevant sections below.


**Run ID:** ___  **Tester/date:** ___  **Overall status:** UNTESTED

Use the [runbook](tax-code-probes-extended.md). Fill blanks with observations or `unavailable`, never inferred
numbers. Duplicate the per-experiment section for each channel/scope/scenario. Keep raw evidence
for failed runs. A visible modifier, a valid parse or a successful button click is insufficient.

## Environment and provenance

| Field | Recorded value |
|---|---|
| PR branch / exact commit SHA | |
| Game version / checksum | |
| DLC | |
| Enabled mods and load order | |
| Enabled mod game rules | |
| Generated effect/trigger/modifier docs version, generation date, vanilla-only or modded | |
| Fresh launch or hot reload? Startup errors? | |
| OS / CPU / RAM / GPU | |
| Simulation speed / resolution / UI scale | |
| Baseline save name/hash and game date | |
| Country tag / market owner / subject status | |
| Active taxation/trade laws and amendments (including on other laws) | |
| Tax level / existing goods taxes / tariffs / subsidies | |
| Relevant treaties / cooldowns / DLC restrictions | |
| Carbon policy and other retained contributors | |
| Reproduction/deployment notes | |

## Predeclared measurement contract

- Control saves and repeat count: ___
- Dates of paused, daily and weekly samples: ___
- Settling interval and measurement window: ___
- Gross assessment/payable base source and units: ___
- Absolute tolerance (£/week): ___; relative tolerance: ___
- Observed control noise and how measured: ___
- Performance speed, warm-up, three control/treatment durations, country count: ___
- Performance rejection thresholds (defaults: 5% closed, 10% open, 250 ms stalls): ___
- Any changes to the contract made **before** the run: ___

## Capability ledger

Allowed status: **UNTESTED / PASS / FAIL / INCONCLUSIVE / NOT RUN**.
“PASS” refers only to the stated capability/scope, not the whole design.

| ID | Capability / required subcases | Status | Evidence IDs | Supported scope / fallback / remaining question |
|---|---|---|---|---|
| P00 | Unarmed isolation; tab read-only; native GUI versus script observations; zero-rate bases | UNTESTED | | |
| P01 | Wage payer deductions / receipts / all five levels | UNTESTED | | |
| P02 | Dividends; remote owners; unprofitable and cooperative cases | UNTESTED | | |
| P03 | Rural monetary assessment; peasants / dependents / units | UNTESTED | | |
| P04 | Head assessment; non-peasant coverage / dependents / units | UNTESTED | | |
| P05 | Consumption selection/common rates; native and scripted authority | UNTESTED | | |
| P06 | State/sector relief; collection versus burden; stacking/clamping; capacity/waste | UNTESTED | | |
| P07 | Amendment versus static carrier; repeat apply; political effects; AI/repeal | UNTESTED | | |
| P08 | Separate import/export duties and subsidy economics | UNTESTED | | |
| P09 | Good overrides / level bounds / Trade Advantage order | UNTESTED | | |
| P10 | Treaty and customs-union authority / market changes / cooldowns | UNTESTED | | |
| P11 | Before-change UI interception; other UI / AI / event bypasses | UNTESTED | | |
| P12 | Bounded records / overflow / iteration / duration / save-load | UNTESTED | | |
| P13 | Player two-clause (+ optional customs) package; hold / supersede / expiry / reload | UNTESTED | | |
| P14 | Explicitly armed AI uses identical commands and constraints | UNTESTED | | |
| P15 | Both civil-war outcomes / secession / release / transfers / capital changes | UNTESTED | | |
| P16 | Delivered versus requested institutions / costs / wages / fiscal balances | UNTESTED | | |
| P17 | Law / colonial / monetary adapters; action-time restraint coverage | UNTESTED | | |
| P18 | Contributor/mutation inventory / migration boundaries / performance | UNTESTED | | |

## Per-experiment record (duplicate this section)

**Evidence ID:** ___  **Probe/subcase:** ___  **Scenario S1–S8:** ___

- Exact initial setup and expected result: ___
- Exact button/console command, count, order and game dates: ___
- Country / state / pop / building / owner / good / direction under test: ___
- Relevant native authority, rules, treaty and cooldown: ___
- Control operation and matching save: ___
- Actual outcome, including failures / unexpected intermediate states: ___
- Reproducible after reload? Number of reproductions: ___

| Observation (identify units and source) | Baseline | Control after | Treatment immediate | Treatment daily | Treatment weekly settled |
|---|---:|---:|---:|---:|---:|
| Calendar date / snapshot # | | | | | |
| Legal rate / monetary assessment / selected tariff level | | | | | |
| Effective rate / cap / bounds | | | | | |
| Taxable base (zero-rate availability?) | | | | | |
| Payer workforce / dependents / coverage | | | | | |
| Payer income before tax | | | | | |
| Payer tax deducted by channel | | | | | |
| Payer disposable income | | | | | |
| Gross assessment | | | | | |
| Net domestic receipts by channel | | | | | |
| Collection loss / waste (define it) | | | | | |
| Customs receipts (separate from domestic) | | | | | |
| Subvention expense | | | | | |
| Trade quantity / price / Trade Advantage | | | | | |
| Authority used / available | | | | | |
| Bureaucracy used / available | | | | | |
| Native legitimacy / IG approval / radicals | | | | | |
| Fixed fiscal balance | | | | | |
| Total fiscal balance | | | | | |
| School requested / delivered / script trigger | | | | | |
| Military wage setting / expense | | | | | |
| Monetary target / actual / authority | | | | | |
| Capital controls sampled state / action count | | | | | |

**Reconciliation:** predicted change ___; observed control-adjusted change ___;
absolute residual ___; relative residual ___; predeclared tolerance ___; pass within tolerance? ___

**Evidence coverage:** all payers / selected pops only / no payer aggregate / other ___

**Errors:** complete `debug.log`/`error.log` message and file:line ___

**Conclusion:** PASS / FAIL / INCONCLUSIVE / NOT RUN ___

**Precisely what this establishes:** ___

**What it does not establish / supported fallback / next experiment:** ___

**Attachments:** before/after save IDs ___; screenshot IDs ___; log files/time range ___;
generated-doc excerpt ___; measurement spreadsheet/CSV if used ___

## Native-control and contributor audit

Add rows for every discovered surface; separate manual, script, AI and treaty actions.

| Surface/contributor and source path | Ordinary behavior unlocked | Locked behavior before next tick | Player/AI/event | Statutory / retained / retire | Gap and required hook |
|---|---|---|---|---|---|
| Budget tax levels | | | | | |
| Budget add/remove consumption taxes | | | | | |
| Budget import/export duty/subvention widgets | | | | | |
| Market / goods / state-goods / right-click | | | | | |
| Already-open menus / keyboard shortcuts | | | | | |
| Tax law and amendments on all law groups | | | | | |
| Native AI / events / emergency changes | | | | | |
| Treaty entry / withdrawal / customs-union change | | | | | |
| Carbon fiscal effect versus output/emissions effect | | | | | |
| Capital-control ordinary / emergency / direct write | | | | | |

## Lifecycle and storage trace

For P12–P15, record both countries separately and mark any explicit/manual copying as such.

| Checkpoint/date/country | Stage/revision/version | Operative two rates/customs | Due/expiry (original?) | Containers/owners/count | Native modifiers/amendments | Unexpected merged fields / missing or doubled collections |
|---|---|---|---|---|---|---|
| Draft | | | | | | |
| Approved | | | | | | |
| Reload before commencement | | | | | | |
| Early / due / repeated commencement | | | | | | |
| Conflict hold | | | | | | |
| Supersession / stale expiry | | | | | | |
| Expiry / reload | | | | | | |
| Uprising original | | | | | | |
| Uprising target before any setup | | | | | | |
| Independent wartime changes | | | | | | |
| Loyalist victory before/after rebuild | | | | | | |
| Rebel victory before/after rebuild | | | | | | |
| Release / secession / transfer / capital move | | | | | | |

## Policy-adapter outcomes

| Promise tested | Authoritative source / target | Availability and authority | Action/target versus actual outcome | Costs | Missing hook / false positive / decision |
|---|---|---|---|---|---|
| School delivery and maintenance | | | | | |
| Separate bureaucracy balance | | | | | |
| Military wage action | | | | | |
| Fixed/total balance over declared window | | | | | |
| Named-law enactment and maintenance | | | | | |
| Colonial release/program/stability; fixed target territories | | | | | |
| Monetary target and actual rate | | | | | |
| Capital controls between samples; emergency exception | | | | | |

## Performance and decision

| Configuration | Control seconds (3) | Treatment seconds (3) | Median delta | UI latency/errors | Country count / result |
|---|---|---|---|---|---|
| Closed tab, one armed country | | | | | |
| Open tab, one armed country | | | | | |
| Ten armed countries | | | | | |
| Snapshot clicks / large country | | | | | |

- Candidate first-playable catalog supported by this evidence: ___
- Explicitly omitted/approximated capabilities: ___
- Blocking interception/authority/persistence issues: ___
- Required source/code changes and reruns: ___
- Reviewer and evidence review date (leave blank until reviewed): ___
