# Tax code engine probes — PR #585

**Status: implemented harness; every engine capability is UNTESTED.** This is disposable
instrumentation for the [design](../superpowers/specs/2026-09-29-legislated-tax-code-design.md)
and [plan, packages 0–1](../superpowers/plans/2026-09-30-legislated-tax-code.md), not the tax-code
feature. Offline parsing/tests cannot establish economic incidence, native validation, or GUI
behavior. Complete the [results form](tax-code-probe-results.md) for each run. Retain failed and
inconclusive runs, with logs; do not replace them with an unsupported “works”.

## Start here

1. Use a **copy of a save**, single-player, debug mode, with only this mod enabled. Record the
   actual game build, DLC, enabled game rules, mod commit, hardware, resolution/UI scale, and
   the source/version of your generated script docs. The repository vanilla snapshot inspected
   when building this harness was **1.14.5**, dated **2026-09-30**; that is not your runtime version.
2. Deploy the full PR branch from a complete checkout. Inspect the deployment dry run; a sparse
   checkout can delete textures. Do not enable a second Workshop copy. Restart the game after
   installing the scripts. Archive startup `debug.log` and `error.log` before they rotate.
3. Load the baseline, pause, select the test country, and run **`event te_debug_tax.1`** in the
   console. Vic3 has no CK3-style `effect` console command. Arming only records observations;
   it does **not** change the law, tax level, goods, or rates. Running it again does not reset a run.
4. Open **Timeline Extended → Tax Probes**. The temporary tab is on a second tab row so the
   existing three labels retain their width. It and the launcher work even if the three ordinary
   window systems are disabled. Switching tabs is read-only. All buttons have console equivalents
   in the appendix; use those if a GUI experiment fails.
5. Click **Snapshot**, save as `P00-armed`, and record the same numbers from Budget/Institutions
   and selected pop panels. Snapshots are in country variables beginning `te_tp_` and in
   `debug.log` lines beginning `TE_TAX_PROBE`. Use debug country → View Variables if logs rotate.
6. Only for an isolated domestic bench, click **Zero carrier**. This **replaces your taxation law**,
   including that law's ordinary non-tax effects, and sets native tax level to medium. It does not
   remove goods selections or modifiers on other laws. Confirm all five *effective* domestic rates
   are zero in Budget, and record any remaining contributors. Save this as `P01-zero-carrier`.
   Compare domestic treatments against this carrier save, not against the original economy.
7. **Reload the appropriate baseline between independent experiments.** Clear bench removes only
   probe modifiers/amendments, pending dates/records and the lock; it leaves the native law,
   goods selections, tariffs, military wages and any economic/political consequences in place.
   Disarm also hides the tab and stops its monthly events. Neither is an undo operation.

Stop and mark the affected probe failed/inconclusive if a script fails to load, a button does
nothing, the country scope is wrong, or the log reports an unknown key/scope/accessor. Capture
file/line and the complete diagnostic. Some hooks are deliberately candidates: in particular
**Static wage** tests a tax-scope modifier applied as a country static modifier. A rejection is
useful evidence for the amendment fallback; a displayed modifier without charged payers is not success.

## Measurement contract (declare before testing)

Use the same paused save for untreated and treated runs. Keep country, dates, game speed,
construction, trade, mobilization, buildings, institutions and other policy changes the same.
Record unavoidable AI/market drift. Do not interpret a civil war, price shock or disappearing
trade flow as a clean tax-rate comparison.

- First capture the paused state, then the first daily update, then each of four weekly accounting
  updates. Extend to eight weeks if values are unsettled. Record actual dates; the monthly snapshot
  pulse is **not** a daily revenue recorder. Use manual Snapshot at each measurement point.
- Run the control twice. Record the range of its weekly receipts and payer burdens as the noise
  floor. Predeclare reconciliation tolerance: default **max(£1/week, 1% of gross assessment,
  measured control noise)**. If noise exceeds 5% of the predicted treatment, mark inconclusive
  and choose a larger base/change or a quieter scenario. Do not widen tolerance after seeing a failure.
- Record by channel: effective rate/amount, taxable base and units if obtainable, gross assessment,
  payer deduction, waste/uncollected amount, net treasury receipts, and authority/bureaucracy cost.
  `tax_income` is domestic tax income, **excluding tariffs and external transfers**. Do not use it
  to validate customs receipts. `net_fixed_income` and `net_total_income` are distinct measures;
  establish their coverage against Budget before using either for a promise.
- For income/dividends, test the expected rate delta against the applicable observed income base.
  For rural/head taxes, establish native time conversion and workforce/dependent coverage first;
  do not assume that 0.1 means a percentage or multiply it by total population.
- Where full payer aggregates are available, test `gross assessment ≈ payer deduction` and
  `gross assessment ≈ net receipts + lost/uncollected assessment`, recording the engine's actual
  definitions. If waste is not deducted from payers, record that instead of forcing the identity.
  Representative pops alone establish those pops' behavior, **not** national reconciliation.
  Missing aggregates mean partial evidence/inconclusive, never an invented national base.
- Save before and after each treatment, export the relevant Budget/pop/state tooltips, and attach
  logs and save identifiers. Cross-check logged values against country variables; a silent zero
  from a bad log accessor must not be interpreted as an economic observation.

Performance contract: choose speed and hardware once, run three matched 12-month controls and
three treatments after a three-month warm-up, and compare medians. Initial rejection budgets:
>5% extra simulation time with the tab closed, >10% open, or repeated >250 ms UI stalls opening
or clicking Snapshot. Also test 10 deliberately armed countries. Report raw times and country
counts; these are provisional investigation budgets, not shipping performance claims.

## Scenario saves

| Save | Required properties |
|---|---|
| S1 small | Quiet small country; incorporated capital; wage earners, peasants and dependents |
| S2 industrial | Large country with manufacturing, profitable private ownership and dividend recipients |
| S3 relief | Incorporated and unincorporated states, poor capacity, remote/foreign ownership; record which state is the capital |
| S4 customs | Positive grain imports and exports, another traded good as control, separate duty and subsidy baselines |
| S5 authority | Market leader/member pair, relevant no-tariffs treaty, appropriate DLC; record trade laws and cooldowns |
| S6 institutions | Available schools, room to expand, enough bureaucracy for a control and a separate deficit treatment |
| S7 lifecycle | Save immediately before an uprising, plus branches for loyalist victory and rebel victory; independent wartime changes |
| S8 adapters | Banking policy controls available, one pegged/delegated country, colonial program/release available |

If a scenario cannot be created with the installed DLC or rules, mark it **not run** and state why.
Do not use the script setters' ability to bypass a restriction as evidence that legislation has
legal authority to do so.

## Experiment sequence and decision gates

### P00 — isolation, GUI, and observations

Compare the unarmed save, armed save, open/closed tab, and other tabs. Ordinary controls and game
rules must behave as before while unarmed. Opening/scrolling/tooltips must not advance stage,
revision, snapshot sequence, tax selection or rates. Snapshot increments only the sequence and
observation fields. Toggle countries/observer mode, close/reopen, and test narrow resolution and
UI scaling. In observer mode the existing outer window gate must prevent player-scope reads.

Compare displayed **Live GUI wage/head receipts** against Budget, and cached Script receipts/
balances against their source fields. Live and snapshot numbers need not update at the same
instant. The school readout is a threshold-based floor: −1 means absent, 0–4 are integer lower
bounds, and 5 means at least 5. Compare it against *delivered* and *requested* levels
while expanding, rather than assuming which the native investment trigger means. UI access is
not simulation/AI access. At zero rates, inspect pop income and state revenue: determine whether
an actual script-readable taxable base exists independently of dividing receipts by a rate.
No such base getter is claimed by this harness. If absent, the fallback is explicit approximation.

### P01–P05 — domestic channels and common consumption rates

From the zero carrier, run **Wage**, **Dividend**, **Rural**, **Head**, and **Consumption** separately,
reloading the zero save each time. The rate buttons remove other probe tax amendments, but retain
state/static modifiers so later stacking experiments remain possible. Confirm there are no
unintended residual contributions from amendments on other laws, decrees, carbon policy, or events.

| ID | Treatment | Required observations / reject conditions |
|---|---|---|
| P01 | Wage 0.05, then Zero rates | +5 percentage points; wage-earner deduction and receipts; dividends and peasants are controls. Reject no payer loss or double application. |
| P02 | Dividend 0.05, then Zero rates | +5 points on actual distributed dividends; test domestic/remote ownership, cooperatives, and unprofitable owners. Do not call this wealth/profit taxation. |
| P03 | Rural 0.1, then Zero rates | Monetary assessment: peasants versus farmers/other pops; workforce and dependents; time conversion and incorporation. Do not call it land-value taxation. |
| P04 | Head 0.1, then Zero rates | Non-peasant payer coverage, workforce/dependents and incorporation. Reconcile using observed eligible counts. |
| P05 | Tax grain, Consumption 0.05; add luxury clothes; Consumption high 0.10; Untax grain | Selected goods share one candidate rate. Compare grain/luxury deductions and an untaxed good. Record authority before/after scripted selection, manual native selection, Authority modifier, and removal. Script additions that evade costs are a limitation, not a free-tax design. |

For each, repeat at native very-low through very-high settings. Probe amendments intentionally
have the **same rate at all five levels**. Any rate difference needs explanation; separately record
native legitimacy, radicals/loyalists and IG effects that still vary with tax level. Run zero/nonzero
checks under poor capacity and in unincorporated states, keeping those as separate cohorts.

### P06 — state/sector relief, stacking and collection losses

Apply one verified tax channel, settle, then test **State relief** (capital −50%), **State exempt**
(capital −100%), **Capacity** (+1000 capital capacity), **Waste** (+0.25 capital waste),
**Agriculture** (−50% agriculture building-group tax multiplier), and **Manufacturing** (−50%).
Each click replaces that same modifier; it does not clear the other named modifiers. Repeat on
wage, dividend, rural, head and consumption channels, reloading between cases.

Record capital versus a matched noncapital state, incorporated versus unincorporated, and worker
versus owner savings (including an owner living elsewhere). Stack relief + exemption and relief +
sector once, then click the same button twice: identify additive/multiplicative/clamped behavior
and verify no duplicate modifier accumulation. Capacity/waste must distinguish lost receipts from
reduced payer liability. Move the capital or transfer the treated state on a separate save: these
modifiers stay on the **original state**, because the button targeted it at click time. Production
must decide whether a privilege follows a named state or the capital designation.

### P07 — application carrier, timing and native politics

Compare Wage via amendment with **Static wage** alone on the zero carrier, and with both together.
Inspect load-time errors, effective rates, deductions and receipts. Test add/remove on pause, next
daily tick and next weekly update. Try repeated Rebuild on an operative package. Inspect normal
amendment repeal UI and let the AI govern for a year; record spontaneous removal or extra adoption.
The test amendments refuse ordinary sponsorship, but whether this blocks every native path is
an experiment. Do not infer native tax-level politics are neutral just because all five rates match.
If country static application fails, retain the amendment route only if its economics/lifecycle pass.

### P08–P10 — customs, goods bounds, treaties, and market authority

Use a **native trade-policy save**, not a domestic carrier save unless explicitly comparing both.
Pause and record grain import/export level, legal min/max, effective rate, cooldown, quantity,
Trade Advantage, net receipts/subsidy expense, and relevant treaty/market owner. Reload between
mutations so cooldown and trade adaptation do not confound a direction comparison.

- **P08:** zero, low and maximum duties; low and maximum subventions in **each direction separately**.
  Use the corresponding Import/Export buttons. Exports are a control while testing imports and
  vice versa. Inspect both immediate setting changes and four settled weekly updates. Compare a
  non-grain good. Use native high settings too to determine intermediate factors (the design's
  0.25/0.5/1.0 candidates must be measured on your build).
- **P09:** test Import rate/Export rate (+0.10 maximum rate) separately from Grain import/Grain
  export (+0.10 good override). Change the selected native level without changing the modifier;
  determine how level and maximum combine. Grain max (−1 level) and Grain min (+1 level) test
  numeric level bounds. Try settings outside each bound through native UI and through the probe
  setter. Stack only in a separate run; test contradictory bounds and log clamp/rejection behavior.
- **P10:** repeat as a leader, member, and treaty-constrained country, before/after treaty entry,
  withdrawal and market change. Compare native UI rejection with script setter behavior. Entry
  effects clearing duties may legitimately supersede the test setting: record it, do not reset it.
  Record subsidy handling separately. These are goods/direction probes, not a bilateral tariff API.

For incidence, compare a matched Trade Advantage change with the same legal tariff setting;
record traded amounts, charged amount and receipts. Establish whether Trade Advantage changes the
base before/after tariff computation, or mark unresolved. A successful level setter alone passes
neither economic incidence nor treaty/customs-union authority.

### P11 — interception and bypass map

On a save with taxes/trade enabled, capture native controls unlocked, then click **Lock native UI**.
The prototype gates the five Budget tax-level buttons, the add-consumption-menu button, and the
14 import/export duty/subvention buttons defined in `budget_panel.gui`. Existing validity checks
remain in place. **Unlock native UI** must immediately restore ordinary behavior.

Test Budget, Market/goods details, state-goods view, right-click menus, already-open popovers,
keyboard shortcuts, amendment repeal, law changes, events, treaty entry, native AI and carbon policy.
Record the exact widget/action and whether a change happened *before* the next tick. Shared widget
use may extend the gate to other screens; prove it. Consumption-tax removal and menus defined in
vanilla shared files are intentionally **not claimed covered**. Native AI and script setters remain
unblocked negative controls. There is no periodic reset to disguise bypasses. Any ordinary bypass
means the interception architecture is incomplete; keep the feature experimental and identify the
additional shared control/hook required. The probe tab's direct setters deliberately remain usable.

### P12 — storage, duration, save/load and bounded records

From an armed save click **Append record** twice; **Inspect records** must read 2. A third append
must log capacity rejection and leave the two existing containers and their month/owner fields
unchanged. Save/reload; inspect the list/container references in the save or variable inspector.
Check the owning country, not merely a global count. Clear bench destroys only records owned by
that country. This tests a bounded representation, not arbitrary objects or inherited native lists.

Start **7-day timer**, save at day 3, inspect days 6/7/8 before/after reload. `te_tp_timer` and the
Authority modifier should expire after seven days; the modifier uses a computed duration variable.
A difference distinguishes timed-variable support from computed-modifier-duration support. This
test temporarily removes consumption authority costs and must use its own baseline. The lifecycle
queue below deliberately uses absolute calendar-month indices (`year * 12 + month`, January zero)
so failure of this duration candidate does not invalidate unrelated experiments.

### P13 — two-clause player passage, conflicts and scheduling

Start zero carrier, no other probe treatments. Record receipts and stage 0. Click **Draft two
clauses**: stage 1, changed revision, *unchanged collections*. Click again to revise. **Discard
draft**, save/reload, and check no collection changes. Redraft and **Approve draft**: stage 2,
no collections yet, commencement next calendar month and explicit zero successor one month later.
Approval is a developer stand-in, not political support or a chamber simulation.

Click **Try commencement** early: unchanged. Save/reload at draft, approval, immediately before
due month, operative state and before expiry. At the first country monthly pulse in the due month,
both wage and dividend clauses become operative (stage 3). Observe the first daily/weekly accounting
updates for a missing/doubled interval. **Rebuild operative** twice must not increase rates, revision,
receipts or change dates. At expiry both clauses revert to zero once (stage 5).

Repeat with **Inject conflict** after approval: version differs; due month must hold the whole
package (stage 4) with previous collections intact. There is no silent rescheduling/reapproval;
Clear bench and explicitly start a new run. From an operative package use **Supersede package**:
it installs a zero domestic successor with a new version. The old expiry must log “stale expiry
ignored”, not alter the replacement. Advance across a December/January boundary. Repeat manual
commencement after the monthly pulse to test double execution. Loading after both deadlines may
process commencement and expiry in one event: final state must be zero, with both logs and no
restarted clocks. Calendar-day precision is not implemented or claimed; monthly resolution is the
candidate fallback. Multiple overlapping approved bills remain a production design question.

After P08–P10 pass for the scenario, start a fresh zero carrier with **grain import level zero**,
click **Include customs** before drafting, and repeat. It adds grain low import duty at commencement
and explicit zero duty at expiry. Record all three clauses at the same checkpoints. Native legality
is still whatever P10 established; these direct setters are not a shipping authority adapter.

### P14 — AI uses the same command path

Select an AI-test country by switching to it in debug mode, arm, prepare the zero carrier, and
click **Arm AI sequence**. Switch back to your original country before advancing. Only this
explicitly armed country enters the sequence: first monthly pulse drafts, second approves,
third commences, fourth expires. Inspect it without taking player control where possible; switching
to it pauses the AI stages. Logs/variables must match P13 and deductions/receipts must reconcile.
Repeat with reload between stages, injected conflict, a separate customs-enabled run, and native
AI fiscal crisis. Native AI may change the law/level: that is evidence about bypasses, not permission
to give it free revenue. This tests command parity, not autonomous political negotiation.

### P15 — revolution, secession and territorial lifecycle

Use S7 with a pending package and two containers. On uprising start, logs inspect the original and
uprising countries **without copying anything**. Record whether scalars, dates, amendments,
modifiers and lists actually transferred. Missing inheritance is a measured limitation, not a
harness failure to hide. The raw uprising event runs on the target even if it has no armed marker.

Create separate branches for both victories. To test each side's independent schedule, switch to
that side, arm it if necessary, and explicitly prepare/draft/approve a different-timed package;
record this as **manual setup, not successful automatic copying**. Leave one side at zero and the
other operative. At victory inspect before pressing Rebuild; then Rebuild twice. The winner's
recorded operative value should determine its two clauses and dates should not restart. Native
missing-variable merges can import loser-only queue fields: record every such field and do not
claim coherent reconstruction if they survive. If no armed marker survives, invoke `event
te_debug_tax.91` manually for raw evidence before arming. Repeat secession, country release,
state transfer and capital move. The harness provides observations and a reconstruction candidate,
not the production copy/reunification algorithm promised by the design.

### P16 — service and fiscal obligations

With available schools, capture requested and delivered level and the harness investment trigger.
Request one normal UI expansion, capture immediately, monthly through delivery, and after reload.
Repeat during a bureaucracy deficit (the **Bureaucracy** modifier forces −10000 for an isolated
stress case). Observe native costs, tax/dividend waste, service level and expansion availability.
A deficit by itself must not be classified as failure of a delivered-level promise. If the engine
trigger reports requested level early, it cannot be the sole delivery verifier.

Use **Military wages: low/medium**, measure salary expense and native political effects, and compare
script wage-level observations. Independently track fixed and total balances over at least four
weekly updates; vary construction and one-off income separately to identify accounting coverage.
A wage cut is an action, not proof of a balanced budget. No extra treasury transfer or duplicate
institution charge is created by these probes.

### P17 — law, colonial, monetary and restraint adapters

- Enact Public Schools through normal legislation. The snapshot's `public_schools` flag must remain
  false during debate and change only on actual activation; compare institution availability.
  Repeal, change government and reload. No harness button force-enacts this promised law.
- Use an existing colonial program/release action in S8, recording eligibility, authority, costs,
  program active state, target-state owner/status and stability before/after each monthly tick.
  Keep target territories fixed in the form. A program purchase is not proof of a stability or
  release outcome. Test target loss, release, transferred obligations and game rule disabled.
- In Budget's monetary controls, legally request a target cut. Snapshot target and actual rate are
  separate (`-999` means unavailable). Compare immediate and monthly values, then test pegged and
  delegated regimes and loss of authority. Use the existing system's controls and native costs;
  never write the target variable directly to manufacture permission.
- With capital controls initially off, activate then deactivate them using the normal policy
  controls **between monthly snapshots**. The sampled active flag may be zero, but the sticky
  `controls_actions` count must increase. The temporary observer is in the ordinary activation
  helper and emergency peg-defence helper; it records **action attempts**, not automatic proof
  that controls took effect. Capture active state after each action. Exercise player, AI, event,
  emergency and game-rule-disabled paths. Search for direct modifier/variable writes not covered
  by those two hooks. Any missed path means continuous restraint is unsupported until instrumented.

These experiments verify candidate adapter inputs and hooks; they do not grant political rewards,
track production obligations, replace diplomatic consent, or silently execute promised policy.

### P18 — migration contributors, zero bases and performance

Run `python3 scripts/analysis/inventory_tax_probe_sources.py` to inventory candidate tax contributors
and GUI mutations from the current repo plus its vanilla snapshot. The output is a starting map,
not a full engine inventory: shared vanilla GUI, hardcoded AI and event files absent from the
snapshot need an installed-game inspection. Classify each contributor in the results form as
statutory provision, retained adjustment or obsolete path; flag any that cannot be intercepted.
Include amendments on non-tax laws, carbon policy/output effects, goods authority and subsidies.

Compare native baselines with a manually equivalent carrier schedule **only where rates match**.
The harness has a deliberately small rate catalog and cannot faithfully migrate every native code.
Do not count it as a completed migration. Repeat rate application/removal and test zero-receipt
bases, as in P00/P07. Run the predeclared performance protocol with GUI closed, open and repeated
manual snapshots. Automatic work is one constant-size monthly event per armed country; no normal
country receives containers, snapshots or collection changes, and no GUI frame runs a world/pop sweep.

## Capability ledger and exit rule

The [results form](tax-code-probe-results.md) starts every row UNTESTED. Give each conclusion a
scenario/save, raw readings, log evidence and its precise scope. PASS requires no unexplained script
errors and the predicted economic/lifecycle behavior within the declared tolerance. FAIL means a
reproduced contradiction; INCONCLUSIVE means missing evidence/noise; NOT RUN means unavailable setup.
A negative capability result may be a successful investigation, but must not be labeled supported.

Amendments instead of static rates, common consumption rates, broad state relief, goods-level
customs, approximate previews and monthly schedules are candidate fallbacks. Unsupported wealth,
inheritance, corporate-profit, land-value or partner-specific taxes stay omitted. No production
architecture is chosen by this PR. Required unresolved interception/authority/persistence gates
keep the design experimental. Attach the completed form to PR #585; do not merge it as “verified”
until its evidence is reviewed.

## Removal before release

Delete the dedicated `te_debug_tax*` files under `common/`, `events/`, `gui/` and `localization/`,
plus `common/laws/zz_te_debug_tax_carrier.txt`. Remove the marked additions in
`gui/te_systems_window.gui`, `gui/budget_panel.gui`, `common/scripted_guis/te_system_tab_sguis.txt`,
`common/scripted_effects/banking_policy_effects.txt`, and
`common/scripted_effects/te_monetary_arrangement_effects.txt`. Remove the probe-specific test file;
retain this runbook, source inventory tool and filled evidence for design decisions. If the
localization organizer has moved keys, also remove the `te_tp_`, `amendment_te_tp_` and
`law_te_probe_carrier` keys from their new localization files. Reload an
unmodified baseline save after removing the carrier definitions. Ordinary player-guide chapters
and PDF are unchanged because the harness is console-only developer instrumentation.

## Console/button appendix

Every numbered command is `event te_debug_tax.N`. All except `.1` require an armed
country. The GUI and console invoke the same hidden country event; the event rechecks its
conditions. Numbers `.90` (monthly dispatcher) and `.91` (raw inheritance inspection) are
internal, with `.91` also useful manually as described above.

| N | Button | Experiment group |
|---:|---|---|
| 1 | Arm probes | Setup |
| 2 | Snapshot | Setup |
| 3 | Zero carrier | Setup |
| 4 | Clear bench | Setup |
| 5 | Disarm | Setup |
| 10 | Wage 0.05 | Domestic |
| 11 | Dividend 0.05 | Domestic |
| 12 | Rural 0.1 | Domestic |
| 13 | Head 0.1 | Domestic |
| 14 | Consumption 0.05 | Domestic |
| 15 | Consumption High 0.10 | Domestic |
| 16 | Zero rates | Domestic |
| 17 | Tax grain | Domestic |
| 18 | Untax grain | Domestic |
| 19 | Tax luxuries | Domestic |
| 20 | State Relief | Modifiers |
| 21 | State Exempt | Modifiers |
| 22 | Capacity | Modifiers |
| 23 | Waste | Modifiers |
| 24 | Agriculture | Modifiers |
| 25 | Manufacturing | Modifiers |
| 26 | Authority | Modifiers |
| 27 | Import Rate | Modifiers |
| 28 | Export Rate | Modifiers |
| 29 | Grain Import | Modifiers |
| 30 | Grain Export | Modifiers |
| 31 | Grain Max | Modifiers |
| 32 | Grain Min | Modifiers |
| 33 | Static Wage | Modifiers |
| 34 | Bureaucracy | Modifiers |
| 40 | Import no | Customs |
| 41 | Import low tariffs | Customs |
| 42 | Import max tariffs | Customs |
| 43 | Import low subventions | Customs |
| 44 | Import max subventions | Customs |
| 45 | Export no | Customs |
| 46 | Export low tariffs | Customs |
| 47 | Export max tariffs | Customs |
| 48 | Export low subventions | Customs |
| 49 | Export max subventions | Customs |
| 50 | Tax level: very low | Controls |
| 51 | Tax level: low | Controls |
| 52 | Tax level: medium | Controls |
| 53 | Tax level: high | Controls |
| 54 | Tax level: very high | Controls |
| 55 | Military wages: low | Controls |
| 56 | Military wages: medium | Controls |
| 57 | Lock native UI | Controls |
| 58 | Unlock native UI | Controls |
| 60 | Draft two clauses | Lifecycle |
| 61 | Approve draft | Lifecycle |
| 62 | Try commencement | Lifecycle |
| 63 | Discard draft | Lifecycle |
| 64 | Inject conflict | Lifecycle |
| 65 | Rebuild operative | Lifecycle |
| 66 | Arm AI sequence | Lifecycle |
| 67 | Append record | Storage |
| 68 | Inspect records | Storage |
| 69 | Start 7-day timer | Storage |
| 70 | Supersede package | Lifecycle |
| 71 | Include customs | Lifecycle |
