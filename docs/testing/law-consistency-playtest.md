# Law consistency: play-test list

What only the game can show about the laws the mod puts in place by script: the consistency sweep
(`gen_law_consistency.py`, `te_fix_inconsistent_laws`), `fix_incompatible_laws`, `te_frontier_ai_fix_law` and the
banking cascade. Each marks the country with `te_law_sweep_replacing` around its `activate_law`, and
`te_law_sweep_notice_from_law_scope` (`extra_on_actions.txt`) reads the mark. In-game checks don't gate a merge
(CLAUDE.md, "In-game checks"); each PR adds its own section, newest last.

## How to run

- **Logs.** Read `debug.log` for the self-check lines (`scripts/analysis/log_triage.py` lists them under Self-checks),
  then `error.log`.
- **Saves.** `scripts/analysis/save_country_probe.py <save> --tag <TAG> --tag <ORIGIN> --laws` gives each law group's
  law and the one before it (`replaced`) for an uprising and the country it rose against; `--diff <before> <after>`
  compares two saves. The watcher's autosaves usually have one either side of a line. Name a country from its log line
  or from loc, never by guessing from a tag.

## A replacement in a half-built country (#1852, 2026-11-27)

The engine builds a revolution's country law by law, each firing `on_law_activated`, and a group it hasn't reached yet
still holds its file's first law (`law_chiefdom` in Governance Principles, `law_no_campaign_finance_laws` in Electoral
Finance). A sweep run mid-build that judged a copied law against such a placeholder would replace a law the origin
held: reading A of #1852. Kalat's uprising (1978.10.4, #1923) was reading B: the sweep judged a law the uprising really
held. The log alone cannot tell the two apart, so a self-check reads it. It changes no behaviour.

### Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … law_sweep_unbuilt_country` | Each line once a game, on a marked replacement after 1836.3.1 (`te_law_sweep_unbuilt_selfcheck`, `extra_effects.txt`). BROKEN: the country has no ruler, holds Chiefdom and is not decentralized. OK: the first replacement in a country that has a ruler. | The check ran. A game with an OK line and no BROKEN line saw no replacement in a ruler-less Chiefdom country. | A law was put in place while the country still held the Chiefdom placeholder: reading A. Read the nearest save with `--laws` for the country and its origin: a group holding its file's first law, or a law the origin held that was replaced, confirms it. | Both law-activated wrappers (`fix_incompatible_laws_from_law_scope`, `te_fix_inconsistent_laws_from_law_scope`) wait while `owner = { NOT = { exists = ruler } }`, and the monthly pulse sweeps the country once it is whole. |
| `TE_SELF_CHECK INFO law_sweep_new_country` | Once a game, on a marked replacement after 1836.3.1 in a country with no ruler whose Governance Principles isn't Chiefdom | No verdict. A new country, judged against laws it holds (reading B). Read which law it got (`law=`) and whether the owner wants that outcome. Kalat's uprising got Single-Party State this way, though it had a ruler, so its line would have been the OK one. | (none) | An owner call, not a fallback: whether a revolution's demanded law should be kept over the sweep's choice. |

Each line names the country from inside its own scope (`country=`, `tag=`), the law put in place (`law=`, from the
saved scope the notice reads, so it may print blank) and the date. If no line of the check appears in a long game,
search for `loc string 'TE_SELF_CHECK` too: a line the engine can't render is dropped whole.
