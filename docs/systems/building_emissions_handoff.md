# Building emissions implementation handoff

Draft PR: [#681](https://github.com/jakeOmega/Vic3TimelineExtended/pull/681).
Branch: `codex/building-emissions`. Base: `ba906c2b` from `origin/main`,
pulled on 2026-10-03. The working tree was clean when work began.

Read `building_emissions_design.md` first. Its latest version is the A′ design,
not the superseded building-percentage draft: separate capture groups, 25/50/75%
tiers, power/steel/chemical coverage, state capture credit, a Tier II mandate,
coal/oil factors 2/1.74, and display-only scaling by 1000.

## Current checkpoint

- Latest main fetched and pulled; feature branch created.
- Repository guidance read (`CLAUDE.md`, docs index, player-guide style).
- Phase-0 opt-in overlay prepared at `docs/testing/carbon_capture_probe/`.
  Its README has deployment/removal instructions, exact checks and a pending
  evidence table. It does not affect normal deployment or market emissions.
- Phase 1 implemented: factors, generated synthetic credits, steel recipes,
  display scale, guide chapter 14 and rebuilt PDF. See design §0 for details.
- `gen_carbon_capture_pms.py` generates synthetic credits and visible emissions
  for 18 fuel methods across power/steel/chemical buildings. `pm_emissions.py`
  derives values from merged recipes and factors, amends mod-owned/REPLACEd PMs
  in place and emits INJECTs for untouched vanilla methods. Extend it for
  production capture variants in phase 2.
- The server on port 8950 did not respond during the initial status check.
- Shared Python environment: `/home/jakef/src/Vic3TimelineExtended/.venv`.
- Git operations need sandbox escalation because this managed worktree stores
  metadata under `/home/jakef/src/Vic3TimelineExtended/.git/worktrees/`.

## Next work

1. Run the opt-in phase-0 engine probe and record results in its README.
   First owner logs confirm nonzero state reads (see probe README). This does
   not yet verify exact staffing/throughput scaling, tooltips or forced fallback.
2. Judge phase 1 in a real save: oil-heavy markets should emit less, electric
   furnaces should show 10 coal and 50/170 electricity, shares and temperature
   must keep their scale, and displayed amounts should render in K/M units.
3. After recording the engine checks, implement phase 2's generator and capture
   integration. If hidden variants fail, use design §8's B fallback.

## Remaining verification

Exact phase-0 scaling, revised net-emissions tooltips, forced fallback and
phase-1 balance review are pending; nonzero state reads have been observed.
No game save has been changed; the test deployment is recorded below. Preserve internal snapshot/history/AI/temperature units when
scaling display values; the live world-emissions script value also feeds the
debug snapshot helper, so do not scale that internal calculation.

Commit and push each coherent checkpoint, updating this file in that commit.
The user explicitly authorized frequent commits and pushes. Do not merge or
publish a finished release before engine verification and balance review.

## Offline checks

- All 3,607 unit/integration tests passed (58 environment-dependent skips).
  The 13 new recipe/accounting tests are in `test_building_emissions.py`.
- Ruff, player-guide strict style, PDF freshness, post-load roster, localization
  sanity/organization, Paradox tab formatting and diff whitespace checks passed.
- All 23 offline CI audits passed.
- Snapshot-backed ModState structure audit: zero unreviewed flags, zero parse
  failures. Nine new/probe script files have one BOM and parse successfully.

Useful commands (use the shared environment above for Python dependencies):

```sh
python3 gen_carbon_capture_pms.py --check
python3 -m unittest test_building_emissions test_resource_transition test_global_warming_layout
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

All 25 emissions tests pass and the guide PDF is rebuilt for this checkpoint.
Next: finish the owner's requested national Atmospheric Carbon Removal policy
(required subsidies and a small environmental movement satisfaction bonus).
Policy work is in progress in separate unstaged files; the removal-only PM
checkpoint is independently reviewable. Commit and push smaller checkpoints.
