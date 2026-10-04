# Building emissions implementation handoff

> Temporary feature-branch continuation log; the durable implementation and
> pending engine checks live in building_emissions_design.md §0. Historical
> checkpoints below may describe superseded formulas or balance.

Draft PR: [#681](https://github.com/jakeOmega/Vic3TimelineExtended/pull/681).
Branch: `codex/building-emissions`. Base: `ba906c2b` from `origin/main`,
pulled on 2026-10-03. The working tree was clean when work began.

Read `building_emissions_design.md` first. Its latest version is the A′ design,
not the superseded building-percentage draft: separate capture groups, 25/50/75%
tiers, power/steel/chemical coverage, state capture credit, a Tier II mandate,
coal/oil factors 2/1.74, and display-only scaling by 1000.

## Current checkpoint

- Feature branch contains latest `origin/main` (`c59e8a36`), fetched again before
  the latest deployment. Review fixes are validated and deployed; checkpoints
  and feedback IDs are recorded at the end of this file.
- Repository guidance read (`CLAUDE.md`, docs index, player-guide style).
- Phase-0 probe assets remain under `docs/testing/carbon_capture_probe/` for
  historical evidence. The overlay is removed from deployment; do not restore
  it alongside production capture because it would duplicate credits.
- Phase 1 implemented: factors, generated synthetic credits, steel recipes,
  display scale, guide chapter 14 and rebuilt PDF. See design §0 for details.
- `gen_carbon_capture_pms.py` generates synthetic credits and visible emissions
  for 245 fuel methods across 117 building types, plus net synthetic/removal values. `pm_emissions.py`
  derives values from merged recipes and factors, amends mod-owned/REPLACEd PMs
  in place and emits INJECTs for untouched vanilla methods. Extend it for
  future coverage/exceptions alongside `pm_carbon_capture.py`.
- Era-10 Direct Air Capture and national Carbon Removal Support are implemented;
  see the checkpoints below for recipes, policy effects and pending engine checks.
- Annual warming now uses state mirrors of building emissions, source capture,
  household heating and atmospheric removal. The three household policies can
  eliminate the household component. See the latest checkpoint below.
- The server on port 8950 did not respond during the initial status check.
- Shared Python environment: `/home/jakef/src/Vic3TimelineExtended/.venv`.
- Git operations need sandbox escalation because this managed worktree stores
  metadata under `/home/jakef/src/Vic3TimelineExtended/.git/worktrees/`.

## Next work

1. Restart on the deployed `codex/building-emissions` branch. The production
   capture controls replace the old probe; do not restore the overlay.
2. Verify January warming/market totals use the PM greenhouse-gas values:
   alter fuel PMs, source capture, staffing and throughput and compare the
   generated state mirror with the sum of building contributions.
3. Compare household contributions before/after Green Building Codes (60%),
   Renewable Investment (25%) and Fossil-Fuel Divestment (15%); all three should
   eliminate this component without suppressing industry or atmospheric removal.
   National cuts must not change another country's households in the market.
4. Check DAC/synthetic PM changes replace their atmospheric credits once.
   A market with enough atmospheric removal can remain net negative even with
   industrial policy reductions. Source capture alone must not cause cooling.
5. Check foreign-owned phaseout buildings whose owner lacks CCS; localized
   state-modifier tooltip lines; 114 hidden variants per technology; AI electricity
   prices and mandate repeal/re-enactment churn.
6. Finish expanded production regression: independent automation/company
   controls; fuel/zero-fuel/feedstock/mobile swaps under the mandate; old-save
   phaseout fallback without CCS after a monthly pulse. Review balance before
   merging. Remaining scope gaps are documented in the latest checkpoint.

## Remaining verification

The owner confirmed all three original in-game test bundles. Generated
production methods, expanded coverage, building-driven warming and household
policy reductions still need regression/balance review. Preserve internal snapshot/history/AI/temperature
units; display scaling remains confined to amount readers.

Commit and push each coherent checkpoint, updating this file in that commit.
The user explicitly authorized frequent commits and pushes. Do not merge or
publish a finished release before engine verification and balance review.

## Offline checks

- All 3,649 unit/integration tests passed (58 environment-dependent skips).
  The 51 emissions/capture/household tests are in `test_building_emissions.py`,
  `test_pm_carbon_capture.py` and `test_household_emissions.py`.
- Ruff, player-guide strict style, PDF freshness, post-load roster, localization
  sanity/organization, Paradox tab formatting and diff whitespace checks passed.
- All 23 offline CI audits passed.
- Snapshot-backed ModState structure audit: 558 files, zero unreviewed flags
  and zero parse failures. Modified script files pass BOM/tab checks.

Useful commands (use the shared environment above for Python dependencies):

```sh
python3 gen_carbon_capture_pms.py --check
python3 -m unittest test_building_emissions test_pm_carbon_capture test_household_emissions test_resource_transition test_global_warming_layout
python3 scripts/analysis/check_post_load_rosters.py
python3 scripts/build_player_guide.py --check
```

The engine probe logs through a ROOT-scoped script-value wrapper, avoiding
`debug_log`'s restricted variable/loc accessor support. Scope dumps identify
each state; the oil fallback in the probe deliberately has no costs. Both
probe textures reuse existing modern plant icons.

## Pushed checkpoints

- `a1e1ec1b`: initial branch/handoff.
- `e8e1be31`: opt-in phase-0 engine probe.
- `1dc9d7f1`: validated phase-1 implementation and guide.
- A final documentation commit records the draft PR link.
  The working tree should be clean at handoff.

Phase 1 is deliberately reviewable separately from capture's additional
balance changes. The next implementation depends on real engine evidence,
not on an unresolved design preference; the owner decisions are already final.

## Test deployment (2026-10-03)

The feature branch was released from the agent worktree for checkout. Another
active task switched the shared main checkout back to the performance branch
while deployment was being prepared, so testing uses an isolated full checkout:

- Path: `/home/jakef/.codex/worktrees/f848/Vic3TimelineExtended`.
- Local integration branch: `codex/building-emissions-test`.
- Integrates the emissions feature and performance tip `fd5f0c35`, retaining
  the company-building BOM fix and current performance work. Do not push this
  integration branch as the emissions feature PR; keep that PR scoped to
  `codex/building-emissions`.
- Target: `/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended`.
- Normal deployment plus the opt-in phase-0 overlay, including English-label
  copies for all supported languages. The next normal deploy removes the probe.
- Integration checks: 125 focused tests passed; deployment dry run had zero
  deletions. The shared checkout's seven modified generated docs were preserved.

Restart Victoria 3 and use a copied save. Console: `event te_cc_probe.1`.
The probe README records the first state-read evidence; remaining checks are
pending. The revised net-emissions overlay needs a new deploy and game restart.

Deployment verification: 27 deployed source/probe files matched by SHA-256;
the company-building single-BOM fix was retained. The apply steps completed.

## Owner follow-up: net emissions display

The owner chose net emissions per building: fuel PMs add a positive
`building_greenhouse_gas_emissions_add`, capture PMs add a negative value.
The state credit is hidden and retained for market accounting. At base
throughput and full staffing, the probe's modern coal plant shows 5.00 − 2.50
= 2.50 per level; modern oil shows 6.09 − 3.05 = 3.04. Include automation fuel.

The owner corrected the design's throughput claim: workforce-scaled modifiers
include throughput, consistent with the repository's scripting guidance.
No throughput caveat belongs in the building tooltip. The current market
consumption formula is retained; fuel-specific input multipliers still need
verification before a building total can replace it.

Households may be omitted if useful, or estimated using population and average
wealth with a hardcoded curve based on buy packages, reduced by appropriate
policies. Record this as an option for future building-based accounting; no
household approximation has been added to the live consumption formula.

Validation of this checkpoint: full suite 3,613 tests passed (58 skips), then
all 21 emissions tests passed after adding recipe-change and cost-annotation
checks. All 23 offline CI audits, Ruff, generator freshness, localization,
player-guide style/PDF freshness, post-load rosters and tab checks passed.
Snapshot-backed structure audit: 552 files, zero unreviewed flags and zero
parse failures. Generator dry run reports 18 fuel methods and no pending writes.

Net-display checkpoint `5adca6df` is pushed. Local test integration `78b9d21a`
included it and performance tip `fd5f0c35`; 142 focused tests passed. A concurrent
deployment replaced the first deployment before verification. Performance PR
#683 then landed on main (`c59e8a36`); feature merge `42ae0f63` includes that
latest main. The same 142 focused tests and generator freshness passed there.

The successful redeploy used `codex/building-emissions` itself, which now
contains the merged performance work. Its dry run had no deletions. Normal
deploy and the revised probe overlay (including all language copies) completed
on 2026-10-03; subsequent SHA-256 verification matched 24 deployed source/probe
files and the company-building single-BOM fix. Restart Victoria 3 before
checking the new Greenhouse Gas Emissions tooltip. The agent checkout remains
on the feature branch; the shared main checkout was not changed by this task.

The final push DNS outage recovered on the next turn; `c9bdc78f` and the
latest-main merge are now on origin.

## Era-10 removal-only checkpoint

The owner requested a Carbon Conversion Works method that stores atmospheric
CO₂ without producing coal. The building now unlocks with the new era-10 Carbon
Capture and Storage technology (prerequisite Clean Energy Technologies), with
Direct Air Capture first in its group. Synthetic Coal remains era 11 through
an explicit Genetic Engineering gate on the PM.

Initial capacity is 840 coal-equivalent units, configured separately from
goods output in `greenhouse_gas_factors.txt`. The generator writes −168.00
Greenhouse Gas Emissions into the removal PM's workforce-scaled block. Inputs:
1,200 electricity, 5 engines, 6 steel, 7 chemicals, 1 electronic component;
5,500 jobs. No goods output. Market accounting reads this staffed/throughput
modifier once and divides by the display scale; Synthetic Coal's separate
branch is explicitly gated to avoid double counting.

Checkpoint `8a7f55c4` is pushed. Its 25 emissions tests pass and the guide PDF
was rebuilt. The removal-only PM is independently reviewable.

## Carbon Removal Support policy checkpoint

The owner added a policy request and reiterated frequent commits/pushes. The
new national policy follows the existing climate policy controls, AI buttons,
counters and treaty repeal restriction. It needs 0.5 °C warming, Carbon Capture
and Storage and more than 100 produced Authority. Effects: required subsidies
for Carbon Conversion Works (both methods), +5% building throughput, 100
Authority upkeep and −5 percentage points Environmental Movement radicalism.
It has no direct emissions multiplier. Its AI threshold is 50 with the usual
15-point repeal band. Existing climate policies retain their effects.

The policy mirrors its state in a country variable and restores its JE
modifier monthly after a revolution. Player/AI controls, active-state queries,
national/global counters and movement satisfaction are connected. The row
reuses the existing Renewable Investment artwork. The guide now covers nine
policies and explains why an unstaffed works removes nothing.

Focused validation: 156 tests passed (27 emissions tests included), Ruff and
GUI lint passed. The full suite then passed: 3,623 tests, 58 skips. All 23
offline CI audits passed. Snapshot-backed structure audit: 554 files, no parse
failures or unreviewed flags. Localization, guide freshness/style, generator
freshness and post-load rosters passed. Checkpoints `8a7f55c4` and `22a672b0`
are pushed. The PM group's label is Carbon Processing, covering both methods.
Next engine checks: research the era-10 technology; build a works and verify
Direct Air Capture is the available default, no coal output, hiring under
subsidies, and removal scaling with staffing/throughput; adopt/repeal Carbon
Removal Support and check subsidy requirement, Authority, movement satisfaction
and January capture totals. Check Synthetic Coal remains unavailable before
Genetic Engineering and switching PMs never counts both credits. The phase-0
fuel gating/mandate checks still gate the production capture-tier rollout.

## Review corrections

Direct Air Capture has no PM-level technology gate: the building itself requires
Carbon Capture and Storage, and captured works must retain a valid default PM
when their new owner lacks that technology. Synthetic Coal retains its era-11
gate. Carbon Removal Support now spells out "carbon dioxide" because the
subscript in CO₂ failed to render in its in-game description. The debug adopt/
repeal-all helpers and AI will logger now include the ninth policy.

After these corrections, 156 focused tests passed, including the 27 emissions
tests; Ruff, localization organization, generator freshness and diff checks
passed. The earlier full-suite result above predates these small corrections.

## Production capture continuation

The owner confirmed all three requested engine-check bundles: fuel gating and
forced fallback with/without the mandate; displayed and logged totals; Direct
Air Capture and Carbon Removal Support. Production source capture is authorized.
The owner also requested coverage of all coal/oil users with deliberate exceptions.
Emissions display now discovers every building PM group, including companies:
245 fuel-consuming PMs across 117 building types. Market gross is still based
on consumption. Capture will use a separate group per fuel-consuming source
group to cover automation without a Cartesian product of PM selections.

Production capture now generates 74 building types, 70 source groups and 342
tier variants. `pm_carbon_capture.py` owns explicit exceptions and cost anchors;
its coverage report lists every inclusion/exception. Automation uses separate
controls, including steel boilers; no Cartesian-product gating. Three existing
shield icons serve as tier artwork. State credits are subtracted once per
location's market and divided by the display scale. No new yearly building sweep.
Tiny sources retain fractional operating costs and capture values to avoid free
capture from rounding. Modern coal Tier II uses 12 electricity rather than the
probe's approximate 11: it rounds the design's 0.30 MWh/t × 3.07 t/coal anchor.

Managed Fossil Phaseout now unlocks with Carbon Capture and Storage. No capture
and Tier I are disallowed; no-fuel/feedstock/mobile exemptions have a valid
not-applicable method. `gen_law_consistency` explicitly rechecks technology for
this held law, leaving other legacy laws' behavior unchanged. The existing
monthly/law-change cleanup handles old saves lacking the new technology.
74 focused tests passed before the production checkpoint. The guide is updated.
Pending: full CI checks, production regression in game (especially independent
automation, company-site controls, NA exceptions and January state subtraction).
Normal production deployment must remove the probe overlay: keeping it could
duplicate state credits and modifier-type definitions. Do not restore it.

Unified accounting follow-up: synthetic methods now show net emissions after
their existing output credits (coal-to-liquids +4.68, synthetic oil −52.20,
synthetic coal −168 per full level). Synthetic methods and Direct Air Capture
feed `state_carbon_capture_add` too. Live market capture is now one market →
countries → states sweep, with no synthetic/DAC building iterations or manual
level/occupancy multipliers. All capture follows staffing and throughput. Legacy
generated synthetic script values remain for compatibility, but are no longer
read by live market accounting. 74 focused tests pass after this change.

Full-suite invocation needs the CI dummy VIC3_* paths documented in CLAUDE.md:
without them, this worktree cannot resolve vanilla_docs_path for server imports.
The first full run therefore had environment import errors; rerun with CI env.
Similarly GUI reference audit against the local installation reports unresolved
engine-library types; the CI (vanilla-unavailable) invocation passes, and the
other 22 CI audits passed. Structure audit: 557 files, zero flags/parse failures.

## Final production checkpoint (2026-10-03)

Pushed: `519df3fa` broad display, `35c1aaeb` production capture and mandate,
`9427659f` unified credits and synthetic net display. The feature branch includes
latest `origin/main` (`c59e8a36`), checked again before deployment.

Final validation: 3,636 full-suite tests pass (58 skips), all 23 CI audits pass
with the documented CI environment, and snapshot-backed structure audit covers
557 files with zero flags or parse failures. Generator freshness, Ruff,
localization organization/sanity, tabs, GUI lint, roster and guide checks pass.
The normal production deploy completed; SHA-256 verification matched all 37
feature game files and all 310 staged language files. The 17-file probe overlay
is removed. The main checkout was not switched.

The draft PR description is current. Remaining work is the generated production
regression/balance review listed in Next work above; no engine tests of the new
342 variants are claimed. Restart Victoria 3 to load the production groups.

## Building-driven climate and household checkpoint

The owner requested replacing gross coal/oil-consumption accounting with the
building GHG values, then adding household consumption and near-complete cuts.
They explicitly clarified that the 100% target is households only.

Generated `state_greenhouse_gas_emissions_add` mirrors gross fuel contributions
and negative source-capture contributions; synthetic/DAC atmospheric credits
are separate in `state_atmospheric_carbon_capture_add`. Live annual market
emissions now sum each state's remaining industry after the leader's policy
cut, plus that state's household estimate, minus full atmospheric removal.
Source capture and the industrial policy multiplier cannot by themselves make
industry remove carbon. Display/history/temperature units are preserved.

Households use state population × interpolated heating demand at average_sol,
normalized by the vanilla 10,000-person package and baseline consumption
equivalent 0.625 (25% workers plus 75% dependents at half needs). Heating budget
is assigned 20% coal, 30% oil and 50% non-fossil at merged base prices. This is
an estimate, not an exact pop-only sales accessor or a change to buy packages.
The curve and prices regenerate through `household_emissions.py`.
Green Building Codes −60%, Renewable Investment −25%, Fossil-Fuel Divestment
−15% stack additively on `country_household_greenhouse_gas_emissions_mult`,
floored at zero; national cuts apply to the state's owner, not market neighbors.
Public Transit targets transport rather than this direct fossil-heating estimate.

79 focused tests pass, including 11 numerical regressions using production
script-value ASTs. Full validation and deployment are complete below; engine
checks for mirrors, January totals, household policy adoption/repeal and cooling
remain pending.
Standalone military-unit fuel is outside the building-PM mirror; civil transport
PMs remain included. Fuel-specific input multipliers are not automatically
applied to custom PM GHG mirrors. A future extension can model those separately.


## Validated building/household deployment (2026-10-03)

Implementation checkpoint `0e2e811b` is pushed. All 3,647 tests pass (58 skips),
all 23 CI audits pass, and the snapshot-backed structure audit covers 559 files
with zero flags/parse failures. Generator freshness, Ruff, localization,
tabs, GUI lint, post-load roster, player-guide style and PDF checks pass.

Before deployment, origin was fetched again and main `c59e8a36` confirmed as an
ancestor. The dry run had no deletions. Normal deployment completed to the
Windows mod folder above; SHA-256 matches all 40 feature game files and all
310 staged language files. The obsolete probe is absent. The shared main
checkout was not switched. Draft PR #681 describes the current implementation.

Restart Victoria 3 before testing. The five checks in Next work are the current
continuation plan. No in-game verification of the new building-driven annual
formula or household estimate is claimed.


## PR review checkpoint (2026-10-03, review 5403672148)

Review items 1–4 are addressed: synthetic output credits now enter net industrial
emissions before the market leader's cut; only DAC writes atmospheric removal.
The Carbon Captured dashboard row now reads atmospheric removal only, and its
tooltip names Direct Air Capture. Carbon Removal Support's coal-works throughput
modifier is registered. All three state accounting types have names/descriptions
in localization; script-only does not guarantee hiding from tooltips.

Inline comments addressed: 4175604053, 4175604258, 4175604463. Numerical
regressions cover synthetic fuel production/combustion at 0/50/75/100% policy
cuts, preserving DAC's full credit. Further review work: household calibration,
fuel-input policy effects, AI support eligibility, DAC balance, employment-audit
coverage and stale player/developer text. Pending in-game checks remain pending.


## PR review calibration/tooling checkpoint

Review 5403672148: household heating now uses weighted market sell orders for
all heating goods, with weights/caps generated from the merged heating need.
Absent fuels contribute zero. A state-local annual pop sweep weights peasants
by their merged consumption_mult (0.05); state average wealth and the baseline
worker/dependent fraction remain estimates. The three policies still eliminate
household heating. Old fixed 20/30% fossil shares are superseded.

DAC capacity is 210 coal-equivalent units, giving −42 display units per level
with unchanged 1,200 electricity/equipment/5,500 workers. This makes removal
more expensive than the representative Tier II source capture; check subsidy
budget/hiring in game. Synthetic Coal remains 840 output and its credit is
industrial. AI removal-support adoption needs an existing works, and losing
the last works increases repeal weight. Input discounts retain economic effects;
the guide explicitly describes the recipe mirror's limitation and military gap.

Employment audit now removes independent employment-neutral groups with an
unconditional fallback before enumeration, preserving referenced PM gates.
This restores mine coverage without raising its combination cap. 69 focused
tests pass, including large-neutral-group and dependent-gate regressions.
Inline comments addressed: 4175604771, 4175604946, 4175605126.

Generator cleanup removes unused synthetic per-level script values and their
ownership/exclusion rows; there is no save state to preserve. Synthetic recipe
regressions now exercise the live net/state output. Capture localization preserves
comments and version-less keys, and generic Base capture groups use the building
name. The generated coverage report describes current building-based accounting.
Inline comments addressed: 4175605250, 4175605340. This branch handoff is kept
because the owner explicitly requested agent continuity; treat it as a temporary
checkpoint log, with the design's §0 as the durable system description.


## PR review text and continuation checkpoint

Review 5403672148's stale player/developer text is updated: nine policies,
building/household accounting, DAC-only capture row, Tier II mandate, game-rule
off behavior, input-discount and military limitations. Generic Base labels use
building names. Historical design sketches and probe evidence are marked as
superseded/owner-confirmed without inventing missing measurements.
Inline comment 4175605430 is fixed. Comment 4175605652 is addressed by a clear
temporary-session banner and durable checks/decisions in design §0; this handoff
remains available because the owner requested continuity between agents.

Balance follow-ups retained for owner/engine review: heavier capture costs and
UI, concentrated-stream earlier unlocks, coal-to-liquids recipe realism, artwork
choices and actual foreign-owner technology/law scoping. No split or merge is
performed. Fuel-input discounts deliberately remain economic with clear text,
rather than approximating them with a second custom national cut.


## Validated PR review deployment (2026-10-03)

Review 5403672148 and all ten inline comments are evaluated/addressed above.
Pushed implementation checkpoints: `a9336c48` accounting/registration/localization,
`d5e203a9` household/DAC/AI calibration, audit coverage and dead-code cleanup.
The final text checkpoint follows them. No newer comments arrived during this run.

Final full suite: 3,649 tests pass, 58 skips. All 23 CI audits, Ruff, generator
freshness, localization organization/sanity, GUI lint, post-load rosters, modified
Paradox tabs/BOMs and guide style/PDF checks pass. Snapshot structure: 558 files,
zero flags/parse failures. Localization coverage (with installed vanilla English)
has zero unreviewed flags; the three state types are localized. One preexisting
Chemicals-output type missing its vanilla localization was also given a name.
Employment audit covers 545 buildings, enumerates 87, skips zero, and has zero
unreviewed mod findings. A regeneration check preserves comments/version-less
loc keys. CRLF in journal_entry_systems.md is preserved; use
`git -c core.whitespace=cr-at-eol diff --check` for that file.

Main `c59e8a36` was fetched/verified before deployment. The dry run's sole
deletion was the removed legacy synthetic-values file. Apply completed; all
40 feature game files and 310 staged language files match by SHA-256. Obsolete
values and the historical probe overlay are absent. Restart the game for these
changes. The six Next work checks remain pending; DAC now removes 42 per full
level, and Carbon Captured reports DAC only. The PR remains draft/unmerged,
and the recurring review monitor remains active.


## Follow-up review checkpoint (2026-10-03)

Reviews 5403821644 and 5403833930: emissions map colors and treaty 109 now
read guarded January snapshots, avoiding annual market/pop sweeps during UI
refreshes. Household consuming population uses flat total_size additions in
separate non-peasant and peasant sums, retaining the merged 0.05 weight.
The write-only state_carbon_capture_add type, localization and 346 production
PM writes are removed; its historical opt-in probe stays outside deployment.
Synthetic credits still enter net industry, source capture still reduces it,
and DAC alone writes atmospheric removal. Synthetic exports can yield a
negative producing market without DAC; both capture tooltips and the guide
now explain the credit/combustion attribution.

Inline comments 4175753439, 4175753547 and 4175753673: restored explicit
20/15/10% industrial cuts to the climate-policy concept, marked foreign-owner
probe evidence pending, and matched the standard goods-output localization
style for Chemicals. 69 focused tests pass, including map/treaty snapshot
regressions, population partitions and synthetic export neutrality. Broader
validation/deployment follows this checkpoint. The six in-game checks above
remain pending; review automation stays active and PR #681 stays draft.


## Follow-up validation/deployment checkpoint

Implementation commit `8f0cdb6c` is pushed. Full suite: 3,651 tests pass,
58 skips. All 23 CI audits, Ruff, generator freshness, localization organization
and sanity, GUI lint, rosters, modified Paradox tabs, guide style and rebuilt
PDF freshness pass. Snapshot structure covers 558 files with zero flags and
parse failures; localization coverage has zero unreviewed flags. Employment
audit covers 545 buildings, enumerates 87, skips zero and has zero unreviewed
mod findings. The display-values header now documents annual household sweeps
and snapshot-only UI readers.

Deployment dry run had no deletions; apply completed. All 41 feature game
files and 310 staged language files match by SHA-256. Historical probe and
obsolete synthetic values remain absent. Latest main `c59e8a36` is included.
No newer feedback arrived during this run. GitHub CI is monitored after each
checkpoint; use the PR checks for its current result. Restart Victoria 3 for
testing. All six Next work checks remain pending, including foreign ownership
and the new annual household/model totals. PR stays draft/unmerged; review
monitor stays active. Reviews 5403821644/5403833930 and their three inline
comments are handled and recorded above.


## Owner-reported wording sweep checkpoint

The owner supplied a reviewer recheck of f5fb6cef that found unreported stale
policy counts. Corrected the player-facing journal-entry reason and both debug
option labels to nine. Debug adopt/repeal-all already includes Carbon Removal
Support; no effect change is required. Corrected all four widget comments,
current snapshot/population-counter comments, the debug event header and
AI/op-table developer documentation. The treaty-lock comment now correctly
counts eight protected policies (all except adaptation). Historical eight-policy
references and the eight retired no-GW fallback modifiers remain accurate.

Validation: 67 existing climate-layout tests pass, localization sanity and
organization pass, GUI lint has zero errors/warnings, capture generation is
current (zero writes), tabs and diff whitespace pass. journal_entry_systems.md
retains CRLF. Deployment dry run had no deletions; apply completed. All 45
feature game files and 310 staged language files match by SHA-256. CI runs on
the pushed checkpoint. The previous complete suite remains 3,651 tests passing
with 58 skips; this checkpoint changes wording/comments only.

The broader review did not establish that all work is complete. Fuel-input
discounts remain economic only; concentrated-stream unlocks, coal-to-liquids
recipe/artwork, the eventual placement of this temporary handoff and optional
PR splitting remain deferred decisions. All six in-game checks above remain
pending. PR #681 stays draft/unmerged and review monitoring stays active.


## One emissions line checkpoint (2026-10-04)

The owner's screenshot showed Greenhouse Gas Emissions and Industrial
Greenhouse Gas Emissions listed together at the same value: the building
display copy and the state mirror. That settles the pending state-line
visibility check. The generator now writes only `state_greenhouse_gas_emissions_add`
and strips `building_greenhouse_gas_emissions_add` from owned recipes. The
building type and its loc are deleted, and the state line is renamed Greenhouse
Gas Emissions. Accounting is unchanged. The "net emissions display" section
above describes the retired building line. Details: design doc §0, "One
emissions line".
