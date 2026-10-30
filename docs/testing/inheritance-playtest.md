# Inheritance second-wave events: play-test list

The second wave of generation events (2026-10-25; `docs/superpowers/archive/specs/2026-10-08-inheritance-laws-design.md`
§ 11; `docs/systems/mod_systems.md` § Inheritance). They passed the offline gate. In-game checks don't gate a merge
(CLAUDE.md, "In-game checks"); the play-test before a release works through this list. Nothing here rests on an
unverified engine fact, so there is no self-check.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- The events are rare: 10% a year after a generation under the law (`te_inh_law_recent` lapsed), or 25% a year once
  the Endowment has been held five years. The console shows each: `event inheritance_events.14` (its trigger still
  applies).

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | The Hidden Estates | Under State as Universal Heir, 20 years after enacting it. Auditing shows Estate Audits (authority cost, fading) and lowers every state's Wealth Concentration by 3; looking away raises it by 5 and shows Hidden Estates for ten years. | No event after 20 years: check `te_inh_law_recent` with `save_country_probe.py --var te_inh`. |
| 2 | The Empty Holding | Under Possession by Use. The commune's answer shows Repartitioned Holdings (agriculture −3%), the family's Holdings Kept in the Family (+5%) and displeases anarchist-led groups. | |
| 3 | The First Cohort | Five years after the Birthright Endowment is attached (`te_inh_endowment_years` counts the years). It comes once; repeal the Endowment and attach it again, and after five more years it can come again. | It comes twice in one tenure: `te_inh_first_cohort_paid` didn't hold. |
| 4 | Tooltips | Every answer that moves Wealth Concentration says by how much; no line shows a raw key. | |
