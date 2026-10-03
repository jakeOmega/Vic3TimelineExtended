# Building emissions implementation handoff

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
- `gen_carbon_capture_pms.py` currently generates only synthetic credits and
  is registered before organize_loc. Extend it for capture variants in phase 2.
- The server on port 8950 did not respond during the initial status check.
- Shared Python environment: `/home/jakef/src/Vic3TimelineExtended/.venv`.
- Git operations need sandbox escalation because this managed worktree stores
  metadata under `/home/jakef/src/Vic3TimelineExtended/.git/worktrees/`.

## Next work

1. Run the opt-in phase-0 engine probe and record results in its README.
   All six fixture script files parse offline. This does not verify staffing
   reads, tooltips or forced fallback in Victoria 3.
2. Judge phase 1 in a real save: oil-heavy markets should emit less, electric
   furnaces should show 10 coal and 50/170 electricity, shares and temperature
   must keep their scale, and displayed amounts should render in K/M units.
3. After recording the engine checks, implement phase 2's generator and capture
   integration. If hidden variants fail, use design §8's B fallback.

## Remaining verification

All three phase-0 in-game checks and phase-1 balance review are pending.
No deployment or game save has been changed. Preserve internal snapshot/history/AI/temperature units when
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
- Phase-1 commit follows those two; use `git log -3 --oneline` for its ID.
  The working tree should be clean at handoff.

Phase 1 is deliberately reviewable separately from capture's additional
balance changes. The next implementation depends on real engine evidence,
not on an unresolved design preference; the owner decisions are already final.
