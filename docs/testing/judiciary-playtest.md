# Judiciary play-test checklist

What the next play-test of the Judiciary law group should look at (spec:
`docs/superpowers/specs/2026-10-17-judiciary-design.md`; systems doc: `docs/systems/mod_systems.md` § Judiciary). In-game
checks don't gate a merge (CLAUDE.md, "In-game checks"): phase 1 landed on the offline gate, and the play-test before a
release works through this list. Where the build rests on an engine fact nobody has verified, it ships the preferred
version with a self-check line in `debug.log` and names its fallback below; a BROKEN line means swap the fallback in.

Each later phase adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`). Check the playset has no Workshop copy of
  the mod.
- **Reading the score.** Hover Judicial Independence in any court law's tooltip: the concept's description ends
  "Now X, heading for Y". `scripts/analysis/save_country_probe.py --var te_jud` reads the variables from a save.
- **Logs.** Read `debug.log`, not `error.log`. Grep it for `TE_SELF_CHECK` first.

## Self-checks (every game)

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … judiciary_enacting_law_scope` | once a game, the first time a country whose court law carries an enactment-success line (Constitutional Review or Judicial Supremacy), and not a paper court, starts enacting any law (in 1836, the United States' first enactment) | `currently_enacting_law` resolves at `on_law_enactment_started`, so entrenchment can see which law is under way | the link is missing at that hook: entrenchment never adds its enactment modifier | move `te_jud_enactment_started`'s work into a hidden country event fired from `on_law_enactment_started`, the route Forceful Legislation (`minor_events_timelineextended.2`) takes |

No line at all after such a country starts an enactment means the hook's ROOT isn't the country; take the same
fallback.

## Phase 1: the law group and Judicial Independence

1. **Lobby (1836).** The United States shows Constitutional Review; Persia, the Ottoman Empire and Egypt Religious
   Courts; Britain, France and Prussia Statutory Courts; Russia and Qing China Executive Tribunals. This shows that
   the scripted effect ran from history (spec § 9).
2. **February 1836.** The Judicial Independence modifier shows in Britain's modifiers with the scaled values (+7
   legitimacy at 70). The concept's description reads "Now 70, heading for 70". Britain (an elected government)
   shows Supremacy of Statute as legitimacy from votes; Prussia, with no voting law, as +25 authority, and its
   concept reads "Now 35, heading for 35" (Autocracy halves its ceiling). History sets both scores, so check a
   seeded country too: Persia and the Ottoman Empire read "Now 10, heading for 20" (half of Religious Courts' 40,
   halved). A seeded country reading 0 means the laws' modifier sums were not in place at its first pulse.
3. **Tooltips.** Each court law's tooltip lists its ceiling and its other lines. Autocracy's lists "Judicial
   Independence Ceiling −50%" and "Courts Can’t Challenge the Government". The country panel's Modifiers tab shows
   the ceiling's breakdown. No line shows a raw key.
4. **Entrenchment.** As the United States, start enacting Universal Suffrage: the enactment's modifier list shows
   "Constitutional Challenge" (−10% enactment success), and the self-check above reads OK. Under Autocracy (any
   paper court) with Constitutional Review, nothing is added.
   The first build (#1022) opened `type = { }` on the law, so this line couldn't fire; since the 2026-10-17
   fix `debug.log` carries no `Inconsistent trigger scopes` line for `te_judiciary_triggers.txt` at load.
5. **Spending.** Forceful Legislation's options show the score's cost (−5, −10, −20). Take one; at the next monthly
   pulse the Judicial Independence modifier is smaller. The tax code's Force Through costs 10.
6. **Shock.** As the United States, enact Executive Tribunals. A week after it passes a hidden event applies Court
   Overhaul, decaying over 5 years, sized by the gap (60 − 10 = 50: about +1pp risk premium and −5 legitimacy),
   with middle-strata radicals (a gap of 40 or more). Then move to Religious Courts while it runs: still exactly
   one Court Overhaul (a smaller gap adds nothing).
7. **Secularizing.** As the Ottoman Empire with Rationalism, enact Total Separation: the courts become Statutory
   Courts. Without Rationalism, Executive Tribunals.
8. **Old save.** A repair ran until 2026-10-22 (#1022); it is gone. A save from before the group now gives every
   country Executive Tribunals and no score. Nothing to test.
9. **Algorithmic capture.** With Algorithmic Governance and Algorithmic Jurisprudence, the country's modifiers show
   Captured Court (+2 override capacity) and the ceiling reads 30.
10. **Revolution.** Let a revolution win in a country with a built-up score (Britain at 70): the winner's concept
    still reads the old score, not half its ceiling (rebels are never seeded, so they inherit it).
11. **Log noise.** Grep `debug.log` for `te_judicial_independence` or `te_jud_` in `Failed to fetch variable` lines,
    above all around 8 January 1836 (the week after history's `activate_law` calls): the shock's trigger reads the
    score behind a `has_variable` test.
12. **AI.** Over 50 years, count court-law changes per country (saves a decade apart, `save_country_probe.py
    --law judiciary`): an AI that flips between court laws chasing approval is a red flag.
