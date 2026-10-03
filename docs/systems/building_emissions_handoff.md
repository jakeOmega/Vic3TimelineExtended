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
- No phase-1 gameplay changes yet.
- The server on port 8950 did not respond during the initial status check.
- Shared Python environment: `/home/jakef/src/Vic3TimelineExtended/.venv`.
- Git operations need sandbox escalation because this managed worktree stores
  metadata under `/home/jakef/src/Vic3TimelineExtended/.git/worktrees/`.

## Next work

1. Run the opt-in phase-0 engine probe and record results in its README.
   All six fixture script files parse offline. This does not verify staffing
   reads, tooltips or forced fallback in Victoria 3.
2. Implement phase 1 independently: shared factors, synthetic credits derived
   from PM outputs, steel input changes, display units, guide and PDF.
3. After recording the engine checks, implement phase 2's generator and capture
   integration. If hidden variants fail, use design §8's B fallback.

## Remaining verification

All three phase-0 in-game checks are pending. No deployment or game save has
been changed. Preserve internal snapshot/history/AI/temperature units when
scaling display values; the live world-emissions script value also feeds the
debug snapshot helper, so do not scale that internal calculation.

Commit and push each coherent checkpoint, updating this file in that commit.
The user explicitly authorized frequent commits and pushes. Do not merge or
publish a finished release before engine verification and balance review.
