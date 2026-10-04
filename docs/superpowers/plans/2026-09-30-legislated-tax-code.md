# Legislated tax code — implementation plan draft

**Status:** core implementation can begin with the limited runtime evidence below; automatic scheduling and integration gates remain unresolved.
**Probe runbook:** [Tax code engine probes](../../testing/tax-code-probes.md).
**Results form:** [Copy for each playtest run](../../testing/tax-code-probe-results.md).
**Runtime evidence:** [2026-10-02 UK first pass and follow-ups](../../testing/tax-code-probe-results-2026-10-02.md) (1.14.5, reported revision `77da24c`).
**Design:** [Legislated tax code and customs schedule](../specs/2026-09-29-legislated-tax-code-design.md).
**Outcome:** a player and an AI country can draft, negotiate, approve, and commence a fiscal package while existing collections continue until its effective date.

The design is authoritative. This plan proposes implementation boundaries and exit criteria;
identifiers, record storage, rate steps, numerical budgets, and exact PR splits remain provisional
until the capability probes establish what works. Every production checkbox below is unfinished; probe implementation does not satisfy its runtime exit gate. A static
hook reference is a candidate, not a passed experiment. Do not implement the entire aspirational
instrument catalog before delivering the supported first playable loop.

## 1. Scope and sequencing

Candidate first-playable instruments are flat wage/dividend rates, native rural/head assessments,
selected consumption goods at a common rate, verified state/sector relief, and separate goods-level
import/export customs settings. Existing subsidies require explicit migration and legal treatment.
Begin promises with institution maintenance and supported fiscal actions/outcomes. Offer only
channels and promises that pass their probes; keep unsupported controls absent from the workbench.

Arbitrary brackets, wealth/inheritance/business-profit/land-value taxes, advanced forecasts, and
full constitutional chambers remain outside this milestone. Political, colonial, monetary, and
restraint promises use the same obligation interface but enter the playable catalog only after
their adapters pass verification. Their absence must not prevent the initial service/fiscal bargain.

| Work package | Depends on | Deliverable and exit gate |
|---|---|---|
| 0. Inventory and experiment contract | Nothing | Source map, scenario saves, explicit evidence and performance criteria |
| 1. Isolated capability probes | 0 | Capability ledger and minimal two-clause player/AI passage experiment |
| 2. Canonical schedule and lifecycle | 1 | Versioned records, timelines, one collection writer, deterministic reconstruction |
| 3. Migration and integration | 2 | Existing economy reproduced; native bypasses closed; customs/carbon policies reconciled |
| 4. Negotiation and obligations | 2–3 | IG fallback and first verified promises work through the same command path |
| 5. Draft/review UI and estimates | 2–4 | Read-only inspection, safe drafting, explainable cached previews |
| 6. AI and complete playable loop | 2–5 | Autonomous drafting/bargaining and legal fiscal responses; no AI exemptions |
| 7. Release validation and documentation | 3–6 | Persistence, economy, performance, UI, and migration gates pass |
| 8. Catalog expansion | 7 plus adapter probes | Additional promises and instruments in separate, evidence-backed increments |

These are reviewable work packages, not a promise of eight fixed-size PRs. Packages 0–6 can land
incrementally behind a campaign-setup experimental rule. None constitutes a released playable
feature alone. Retain the design's release gate if customs authority or native-control interception
cannot be made coherent. No mid-save disable switch before a tested reverse migration exists.

### Starting decisions from the 2026-10-02 probes

The linked evidence records the owner's observations and their limits. Start core
implementation with the amendment carrier: manual commencement collected both flat
wage/dividend taxes, and two rebuilds preserved rates/dates through another game week.
State wage relief and agricultural wage relief worked; the tested agricultural
modifier did not relieve Manor House dividends. Keep other incidence claims unverified.

Use bounded country-variable slots and absolute dates initially; those fields survived
reload. Container count/overflow observations are encouraging, but nested month fields
were not printed by the harness. This is incomplete verification, not a container failure.
Keep approved future changes separate from the active debate even with bounded storage.

Use explicitly approximate estimates. No direct pre-tax pop bases were found in the
bounded documentation search. Script aggregates respond to taxes, but the zero-bench
`tax_income` baseline resembles minting; classify its components before displaying it
as tax receipts. Building `earnings × level` is not a verified tax base.

Begin package 2 on these supported mechanisms; package 0–1 dependencies apply to the
capability being implemented, not as an all-at-once extended-matrix prerequisite.
Full package exit gates and every production checkbox remain unfinished.

Early implementation work must:

- Diagnose and fix automatic commencement at the month boundary. The initial log shows
  commencement and expiry in the same call at 22034, after due month 22033; manual
  commencement and rebuild subsequently worked. Instrument the clock/dispatch guard,
  test both boundaries and duplicate calls, and define handling of genuinely late dispatch.
  Do not change carriers or assume a `>`/`>=` cause from this scheduling failure.
- Establish control of native AI fiscal writes and competent shared-market/treaty customs
  authority before substantial dependent integration. Both were skipped, and their
  invariants remain required before release.
- Verify actual institution delivery before adding service promises, and copying/ownership
  behavior before committing to civil-war reconstruction.

## 2. Proposed file and interface boundaries

Use a `te_tax_` prefix for new state and commands, subject to a collision check. New filenames below
are proposals, not existing APIs. Keep collection application separate from proposal evaluation.

| Area | Proposed new files or existing integration surface |
|---|---|
| Developer harness | `common/scripted_effects/te_debug_tax_effects.txt`, a developer-only journal/buttons, and the existing debug-probe on-action pattern |
| Authoritative state and migration | `common/scripted_effects/te_tax_state_effects.txt`, `te_tax_migration_effects.txt`, `te_tax_collection_effects.txt` |
| Bill lifecycle | `common/scripted_effects/te_tax_bill_effects.txt`, `common/scripted_triggers/te_tax_triggers.txt`, `common/on_actions/te_tax_on_actions.txt` |
| Carrier and collection definitions | A Tax Code law, dedicated amendment definitions, and `common/static_modifiers/te_tax_modifiers.txt` using the proven application path |
| Politics and obligations | `common/script_values/te_tax_support_values.txt`, `common/scripted_effects/te_tax_obligation_effects.txt`, adapter-specific triggers/effects |
| Estimates and display | `common/scripted_effects/te_tax_snapshot_effects.txt`, `common/script_values/te_tax_display_values.txt` |
| Player actions and GUI | Tax-code journal entry, scripted buttons/GUIs, shared journal widgets, and existing `gui/budget_panel.gui` |
| AI | `common/scripted_effects/te_tax_ai_effects.txt`; calls the same validated bill/obligation commands as player actions |
| Existing integration | `common/game_rules/extra_game_rules.txt`, shared civil-war effects/hooks, global-warming effects/buttons, banking and colonial adapters |
| Localization and evidence | A dedicated English localization file; capability ledger and reproducible scenario instructions under `docs/` |

Consult [scripting best practices](../../guides/scripting_best_practices.md),
[GUI style](../../guides/gui_style_guide.md), and the current
[CI workflow](../../../.github/workflows/ci.yml). Preserve the repository's encoding, indentation,
localization, guarded-read, and snapshot conventions. Reuse existing debug infrastructure without
making experiments execute in normal campaigns.

## 3. Package 0 — establish the experiment contract

- [ ] Record game version, enabled DLC, active mod revision/set, and generated-doc provenance.
- [ ] Inventory tax contributors: laws, amendments on any law, static modifiers, goods selections,
      decrees, events, native AI, tax-level political effects, customs/subventions, treaties, and
      market-wide carbon policy. Classify each as statutory provision, retained external economic
      adjustment, or obsolete path to retire.
- [ ] Inventory mutation surfaces beyond Budget, including shared customs widgets, goods screens,
      context menus, treaty entry effects, and emergency actions. Identify what can be intercepted
      before collection changes; a later reset is not adequate interception.
- [ ] Prepare repeatable saves for a small economy, a large industrial economy, a customs-union
      leader/member pair, poor tax capacity, active subsidies, and a looming institution expansion.
- [ ] Establish matched-control timing, measurement windows, absolute/relative revenue tolerances,
      and performance budgets before interpreting results. Record hardware and simulation speed;
      distinguish noise from market movement and delayed accounting updates.

**Exit:** a written runbook with expected results and rejection criteria, not a collection of console
commands without a way to measure economic effects.

## 4. Package 1 — prove the capabilities and their combination

For each experiment log setup, exact operation, payer, scope, before/after values, simulation date,
settling interval, comparison control, result, and supported fallback. Mark results as untested,
passed, failed, or inconclusive. Do not promote an inconclusive row to supported.

- [ ] **Domestic channels:** test each native tax modifier independently at zero and nonzero rates.
      Reconcile payer deductions with treasury receipts and losses. Exercise rural/non-rural payer
      coverage, workforce/dependents, incorporated eligibility, and consumption selections/authority.
- [ ] **Relief:** test state collection and building-group tax multipliers against multiple tax
      channels, including remote ownership. Establish stacking/clamping and actual beneficiaries.
- [ ] **Customs:** test import/export levels separately, goods overrides, maxima/bounds, subventions,
      cooldowns, treaty restrictions, and customs-union authority. Observe receipts, expenses, and
      trade changes; do not equate a rate-setting success with a verified incidence model.
- [ ] **Carrier/control:** compare a neutral-medium carrier law with amendment or scripted-modifier
      application. Verify no residual native tax-level political effects, duplicate application,
      autonomous amendment repeal, or player/AI bypass through another surface.
- [ ] **Observability:** separately establish GUI access and script/AI access for rates, payer bases,
      receipts, fiscal balances, and promise targets. Include bases with zero current tax receipts.
- [ ] **Storage/time:** prove record iteration, date comparison, scheduling resolution, save/load,
      overflow handling, and coherent reconstruction at revolution start and either side's victory.
      Do not assume arbitrary objects, computed modifier durations, or native list inheritance.
- [ ] **Obligations:** verify delivered institution level versus requested expansion, native costs,
      bureaucracy balance, one supported military-spending control, and a defined fiscal measure.
- [ ] **Minimal integration experiment:** with temporary developer UI, draft two verified clauses,
      change neither collection while drafting, record simplified approval, commence together, and
      reconcile receipts. Have an AI country take the same command path. Repeat after reload and
      one scheduled transition; include a customs clause if supported.

**Exit:** publish the capability ledger and choose the supported first-playable catalog. If a required
control cannot be intercepted or records cannot survive lifecycle events, revise the architecture
and repeat the affected experiment before production work. Do not proceed by creating flat treasury
income or by allowing a hidden second collection path.

## 5. Package 2 — canonical state, timelines, and one writer

- [ ] Define schemas for enacted provisions, editable draft, introduced bill, actor commitments,
      approved future transitions, policy obligations, and estimates. Include schema/code/revision
      identifiers, explicit successor rules, provenance, and absolute dates.
- [ ] Choose storage only from proven mechanisms. Document bounds for pending transitions, clauses,
      obligations, and history; reject additions with a clear explanation rather than overwrite
      live records. Approved future changes must free the debate slot even when queues are bounded.
- [ ] Implement commands for create/edit/discard, introduce/revise/withdraw, approve, commence,
      supersede, expire, renegotiate, and reconstruct. Validate legal authority and revision at the
      command boundary; player buttons and AI share those validations.
- [ ] Apply patches to named provisions and approved timelines. Expected expiry and unrelated changes
      preserve a bill; material conflicts invalidate affected commitments and approvals. Define
      same-date ordering and hold the whole package if commencement has unresolved conflicts.
- [ ] Make one effect path derive collection from the canonical enacted state. Reconstruction is
      idempotent and never grants support, repeats completion rewards, or restarts a clock. Retain
      enough versioned state to diagnose interrupted or incomplete application without promising
      unsupported engine transactions.
- [ ] Integrate both revolution-start copying and victory reconstruction with the shared civil-war
      layer. Copy operative/future law, permit independent wartime revisions, and keep the winner's
      complete schedule. Prevent loser-only merged variables from resurrecting deleted provisions:
      validate record ownership/version and explicitly clear obsolete tax records.
- [ ] Define separate initialization for secession/releases and eligibility refresh for territorial
      transfers, capital relocation, and market changes. Reassess obligations without marking them
      fulfilled solely because their responsible country or territory changed.

**Exit:** deterministic lifecycle scenarios pass with the GUI absent. Native modifiers are derived
state; loss of a modifier or journal reinitialization cannot change the legal code.

## 6. Package 3 — migrate and reconcile existing systems

- [ ] Map each existing taxation law/level, goods selection, tariff/subvention setting, and relevant
      concession into the supported schedule before retiring its contribution. Preserve non-rate
      effects deliberately, including authority and administrative costs.
- [ ] Compare pre/post-migration payer burdens and receipts over matched windows. Record discrepancies
      by channel and refuse silent approximations. Repeat migration to demonstrate no further change.
- [ ] Normalize native tax level and route every identified statutory mutation through the code;
      keep retained external adjustments visible in effective rates. Test inactive game-rule behavior.
- [ ] Separate carbon fiscal multipliers from output/emissions effects and preserve market authority
      and emissions-treaty restrictions. Verify the resulting aggregate effects are neither lost nor
      duplicated for leaders and members.
- [ ] Preserve actual no-tariffs treaty behavior and subsidy treatment. Revalidation must account for
      entry, withdrawal, and market membership changes without manufacturing bilateral rate controls.
- [ ] Map or defer native ideological stances, movement demands, petitions, and historical events
      keyed to replaced tax laws. A deferral must not leave impossible objectives or an active bypass.

**Exit:** migration and reconstruction preserve the supported economy within declared tolerances;
all known ordinary mutation paths obey the same legal model.

## 7. Package 4 — negotiation and initial obligations

- [ ] Implement the IG fallback with configurable political-strength threshold, legitimacy condition,
      and final-revision debate duration. Do not count parties and their IGs twice. Keep public
      approval, policy preference, commitment, and passage separate.
- [ ] Calculate bounded, inspectable support reasons from dated snapshots. Prevent material/sector
      double counting and support farming through trivial revisions or overlapping promises.
- [ ] Add an obligation interface: availability/authority, baseline, target, costs/consequences,
      deadline, maintenance/observation window, verification, breach, renegotiation, recovery, and
      reconstruction. The adapter reads authoritative state from the responsible system.
- [ ] Deliver institution maintenance, explicit bureaucracy-balance, a supported military-spending
      action, and a defined fiscal-balance outcome where their probes passed. A bureaucracy deficit
      alone does not breach an institution-level promise. A spending cut does not automatically
      fulfill a separately promised balanced budget.
- [ ] Deduplicate protected existing provision and linked promises; reject contradictory bargains.
      Start maintenance on verified delivery, apply consequences once, and retain clocks across
      reload, elections, constitutional changes, and loss of system eligibility.
- [ ] Keep failed delivery separate from repeal: breach does not automatically remove the tax code.
      Renegotiation of material legislative terms requires renewed approval.

**Exit:** the design's worked example can pass, fail, expire, deliver its education promise, or breach
it, with inspectable reasons and no fabricated service benefit.

## 8. Package 5 — estimates and player workflow

- [ ] Implement one dated economy snapshot and estimates keyed to both code and bill revision.
      Evaluate existing-law and proposed timelines against that same snapshot. Refresh on meaningful
      changes; mark stale/incomplete coverage explicitly.
- [ ] Use verified bases for static estimates. Keep unknown incidence and behavioral responses
      labeled; representative households are a fallback, not exact population-wide forecasts.
      Include subsidy expenses, collection losses, and promise consequences without duplicate charges.
- [ ] Build shared Budget/journal sections for enacted code, draft editor, review, actor reasons,
      obligations, pending commencement, and history. Follow the GUI style guide and expose all
      failing action conditions in tooltips and important conflicts in the review itself.
- [ ] Keep inspection and offer preview read-only. Bind execution to explicit validated commands;
      opening a window cannot initialize legal state, reroll votes, or trigger world-pop sweeps.
- [ ] Exercise narrow layouts, localization, unsupported-category absence, stale revisions, and
      transitions between draft, introduced, approved-future, and operative states.

**Exit:** a player completes the supported bargain without debug controls and can explain the
collection changes, approval requirements, and obligations from the displayed information.

## 9. Package 6 — AI and the complete playable milestone

Start the AI command client in the probe harness; this package makes it autonomous and robust.

- [x] Generate bounded candidate packages from revenue needs and actor preferences. Use the same
      estimates, authority rules, offers, support accounting, and commitment constraints as players.
      (Built statically: plan 2026-10-03 Tasks 18–21, schema "AI legislation".)
- [x] Add revision/acceptance/withdrawal decisions, hysteresis, and legal crisis responses. Count
      future approved changes when planning; avoid emergency behavior that silently sets native rates.
      (Built statically: Tasks 19–21; AI customs waits for the customs probe.)
- [ ] Test small and large countries, revenue shocks, war spending, opposition, low legitimacy,
      *(in game: runbook PT-13, PT-16 to PT-22)*
      already-pending changes, and obligations that become impossible. Log why no legal package is
      viable; do not compensate with free revenue or bypassed passage.
- [ ] Measure candidate counts, snapshot refresh costs, GUI-open overhead, and simulation progression
      *(in game: runbook PT-14 and the profiler recipe)*
      against the baseline. Tune refresh cadence and bounds to the budgets declared in package 0.

**Exit:** both player and AI use the complete draft → bargain → approval → commencement loop,
including at least one supported customs change and a verified promise. Experimental work is not
promoted to playable until persistence and release gates below pass as well.

## 10. Package 7 — validation and release evidence

Use targeted static checks for schema/reference coverage and guarded reads, plus runtime scenarios
for economics and lifecycle behavior. Static tests that merely assert a modifier name exists do not
prove payer deductions, atomic application, or persistence. Follow current CI commands and its
isolated path configuration for implementation PRs; a documentation-only plan needs link and
whitespace checks, not the gameplay suite.

| Scenario | Required observation |
|---|---|
| Draft/edit/discard and failed passage | No collection or reward changes |
| January expiry and February replacement | Both timelines execute as reviewed; no stale snapshot restoration |
| Conflicting commencement and same-date transitions | Whole package holds or executes in approved order; no partial collection |
| Zero-rate channel becomes taxable | Estimate base is available or approximation is explicit; payer/receipt reconciliation passes |
| Relief, subsidy, treaty, and market changes | Correct authority, direction, beneficiaries, costs, and no secondary controls |
| Institution delivery and explicit deficit promise | Native costs apply; independent promises fulfill or breach independently |
| Save/load at each lifecycle stage | Dates, revisions, commitments, and future changes preserved |
| Both civil-war outcomes with different wartime reforms | Winner's coherent schedule restored; no loser-only clauses or repeated rewards |
| Secession, releases, transfers, and moved capital | Explicit initialization and territorial eligibility without reunification mistakes |
| AI fiscal crisis | Same legal constraints, explainable failures, no free collections |
| Disabled rule and repeated migration | Existing behavior retained when disabled; migration idempotent |
| Large-country/world performance and open GUI | Meets declared budgets without per-frame expensive aggregation |

- [ ] Publish scenario results, logs/save comparisons, known limitations, and approved fallbacks.
      *(the instrument is built: runbook `docs/testing/tax-code-playtest.md`, the ledger's evidence
      matrix and known limitations, `scripts/analysis/tax_code_save_report.py`; results pending)*
      Use the existing save-analysis tooling where useful; retain enough setup detail to reproduce.
- [ ] Resolve unexplained economic discrepancies and material script errors before release.
- [ ] Update the capability ledger and design with decisions actually supported by evidence.
- [ ] Update the player guide, system references, and guide PDF for implemented player-facing behavior.
      Do not document deferred controls as available.

## 11. Package 8 — expand policy bargains and instruments

After the complete first playable milestone, implement each adapter as a separate reviewable increment:

1. **Political reforms:** verify named-law enactment and maintenance through normal passage;
   account for incompatible reforms and impossible deadlines. A promise never force-enacts a law.
2. **Colonial actions/outcomes:** freeze agreed target territories/statuses, use existing release or
   program actions, and distinguish funding a program from achieving stability. Audit ownership,
   eligibility changes, and overlapping obligations after releases.
3. **Monetary policy:** honor domestic-rate authority, currency regime, delegation, target-to-rate
   adjustment time, and mandate changes. A target cut and an actual-rate target are different terms.
4. **Restraints:** cover named capital controls with explicit emergency exceptions. Prove action-time
   violation tracking across player, AI, and event paths; monthly sampling alone is insufficient.
   If complete observability is unavailable, defer the promise rather than claim continuous restraint.
5. **Advanced instruments and institutions:** repeat the payer/base/control/preview/persistence gates
   for each new tax or constitutional interface. Preserve the existing code and obligation lifecycle.

Each addition updates offer eligibility, AI evaluation, migration/versioning as needed, display,
localization, runtime scenarios, and player documentation. No adapter should duplicate its source
system's policy costs or benefits, and none should make the original supported loop depend on an
optional system being enabled.
