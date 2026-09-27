# External banking tools — validation (2026-09-27)

## Offline checks

- Full unit suite except `test_reload_post_load`: 1,967 tests passed, 46 skipped. The excluded test can POST to the live server and regenerate the main checkout. Two additional flow tests were then added and passed in the focused 26-test external-policy/roster run.
- Actual-script scenarios cover regime/law gates, funded sterilization, positive/negative gold pressure, gradual FX-debt protection and repeal, reserve-purchase cash conservation, combined treasury bills under immediate and deferred reads, import-finance fatigue and crisis exit, inherited state, and dashboard placement.
- Simulator self-tests pass. Direct flow tests confirm restriction halves arrivals and leaves exits unchanged.
- Full worktree parse against the committed vanilla snapshot: no parse failures. Structure and localization-accessor audits: no unreviewed findings.
- Python lint, localization BOM/header/duplicate checks, and script audits pass (duplicate keys, effect/trigger names, iteration limits, localization references/rendering, modifier multipliers, variable visibility/lifetimes/clamps, JE initialization and empty effects).

## Preliminary balance sample

Commands: `python3 scripts/analysis/banking_cycle_sim.py --runs 30 --years 100 --only gold --points 6 --jobs 2`, with and without `--exclude-tool restrict_inflows --exclude-tool sterilize_inflows`. Default seed and four mandate modes; 120 simulated centuries per arm.

| Gold policy | Baseline crashes/century | With flow tools | Baseline recession months | With flow tools |
|---|---:|---:|---:|---:|
| Manual/no mandate | 7.6 | 7.0 | 6.9% | 6.6% |
| Price stability | 4.1 | 4.9 | 1.4% | 1.8% |
| Growth | 11.6 | 12.8 | 4.1% | 4.7% |
| Peg defence | 9.0 | 10.7 | 5.4% | 6.7% |

These tools are not a universal cycle improvement: they compete with domestic prudential tools for points, and sterilization changes the bank's inflation feedback. This small sample shows a higher crash rate under the three mandates; it is not evidence of a crash-prevention benefit. It is a sensitivity check, not a tuned long-run balance certification.

The cycle simulator has no liquid treasury and keeps FX at par. It assumes funding for sterilization and excludes borrowing limits, surrender and import-finance AI selection rather than inventing those missing inputs. Their script formulas and lifecycle are covered by scenario tests, not this sample.

## In-game checks still required

Check External & Currency row layout and dynamic tooltips; confirm treasury debits appear correctly and imports respond to trade advantage. Exercise gold suspension/resumption, bank repeal, a depleted treasury, a full vault, crisis recovery, and revolution inheritance. Verify treasury-funded reserve accumulation alongside existing bank recapitalization, and inspect longer-run AI adoption before claiming final balance.
