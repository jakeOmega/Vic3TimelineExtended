# Judiciary play-test checklist

What the next play-test of the Judiciary law group should look at (spec:
`docs/superpowers/archive/specs/2026-10-17-judiciary-design.md`; systems doc: `docs/systems/mod_systems.md` § Judiciary). In-game
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

| `TE_SELF_CHECK … judiciary_law_type_variable` | once a game, the first time a Forceful Legislation option is taken under Constitutional Review or Judicial Supremacy (and not a paper court) | a country variable set to a law type reads back as one, so a forced law's case can be filed and compliance can restore the law it replaced | no case is ever filed: the courts never rule on forced laws | file the case from the forced law's own `on_law_activated` (match its type there, as `te_jud_law_activated` does, and fire the ruling on `owner`), and let compliance cost the forced law's legitimacy (`te_jud_ruling_unreversed`, already the fallback branch) instead of restoring the old law |

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
8. **Old save.** Load a save from before the group. Within a month each country holds its rule-based court, and
   within two a score at half its ceiling. No country gets Court Overhaul.
9. **Algorithmic capture.** With Algorithmic Governance and Algorithmic Jurisprudence, the country's modifiers show
   Captured Court (+2 override capacity) and the ceiling reads 30.
10. **Revolution.** Let a revolution win in a country with a built-up score (Britain at 70): the winner's concept
    still reads the old score, not half its ceiling (rebels are never seeded, so they inherit it).
11. **Log noise.** Grep `debug.log` for `te_judicial_independence` or `te_jud_` in `Failed to fetch variable` lines,
    above all around 8 January 1836 (the week after history's `activate_law` calls): the shock's trigger reads the
    score behind a `has_variable` test.
12. **AI.** Over 50 years, count court-law changes per country (saves a decade apart, `save_country_probe.py
    --law judiciary`): an AI that flips between court laws chasing approval is a red flag.

## Phases 2–4: defying the court, amendments, landmark cases (2026-10-25)

Spec § 14. Built before phase 1's play-test, so read phase 1's items first: these rest on the score behaving.

### Phase 2: defying the court

13. **Tooltip.** Constitutional Review's and Judicial Supremacy's tooltips show "Courts Review Forced Laws", and its
    description gives the three thresholds (90, 60, 30).
14. **Opening a challenge.** As the United States in 1836 (Constitutional Review, score 60), give yourself override
    capacity (console, or Autocracy is no use: it is a paper court) and take Forceful Legislation's Expedite option:
    its tooltip adds "Once the law passes it goes to the courts, which strike it down if Judicial Independence is at
    least 90". The self-check above logs once.
15. **Filing and ruling.** Let the forced law pass. Within a month `save_country_probe.py --var te_jud_case` shows
    `te_jud_case_law` and `te_jud_case_filed`; about six months after that the ruling comes. At score 55 after Expedite
    (below 90) it is The Court Upholds the Act; with Force it through (threshold 30) it is The Court Strikes Down the
    Act, and its description names the law. A forced law that fails leaves no case behind.
16. **Comply.** The law in force before the forced one comes back (its tooltip names it), the score rises 5 at the next
    monthly refresh, and Ruling Obeyed shows. **Defy:** the score falls 20 and Ruling Defied raises the risk premium
    by about 1pp. **Pack:** the score falls 15, Packed Court and Packing the Court show, entrenchment stops (start a
    Distribution of Power law: no Constitutional Challenge), and a forced law now opens no case. A year later The
    Enlarged Bench offers Statutory Courts; taking it switches the law at once and ends the packing.
17. **Lawyers in the Streets.** Repeat phase 1's item 6 (Constitutional Review at 60 to Executive Tribunals, a gap of
    50): a week after the change the event appears instead of bare radicals. Its third option raises the score by 10.

### Phase 3: amendments

18. **Debates.** Enacting Statutory Courts or Constitutional Review under an elected government can bring Who Judges
    the Judges? and The Jury Question; Algorithmic Jurisprudence, A Right to a Human Judge. Accepting attaches the
    amendment to the incoming law (the law panel shows it once the law passes) and gives the bill +5% success.
19. **Petitions.** Petitions `.21`–`.27` are rare (2.5%–25% a year, at most one petition in five years): the console
    (`event amendment_petition_events.21` as a country at war under Statutory Courts) shows each. Accepting attaches
    the amendment to the court law in force.
20. **Habeas corpus lapses.** With the Suspension of Habeas Corpus attached, make peace: within a month the amendment
    is gone, and the ceiling's −20% with it.
21. **People's Tribunals lapse.** Leave Single-Party State while Executive Tribunals carry them: within a month they
    are gone.
22. **Human-in-the-Loop.** Under Algorithmic Governance and Algorithmic Jurisprudence, attach the amendment: Captured
    Court disappears at the next monthly refresh and the override capacity falls by 2.
23. **Mixed Commercial Courts** lower the credit standing premium by 0.5pp under Religious Courts (the Ottoman Empire
    in 1836) and raise the ceiling to 50 (25 under Autocracy's halving).

### Phase 4: landmark cases

24. **Each case once.** `save_country_probe.py --var te_jud_heard` lists the cases a country has heard; none comes
    twice. Console: `event te_judiciary_events.30` and so on (each event's trigger still applies).
25. **The Free Soil Case.** The United States with an abolition movement at 5% and a score of 60 or more sees all three
    answers; below 60 the free-soil answer is greyed out. Free Soil Ruling shows the +15% for Slavery Banned in
    the enactment chance once the law is under way.
26. **The Ōtsu Case** names an AI great power, and relations with it move by 20 either way.
27. **Freedom of Contract**'s second answer packs the court exactly as phase 2 does, and The Enlarged Bench follows a
    year later.
28. **The Voided Election** comes right after an election (`on_election_campaign_end`). Declaring the emergency shows
    State of Emergency for three years, and entrenchment and the review of forced laws stop for those three years.
29. **The Doctrine of Necessity.** As Britain (Statutory Courts, 70), enact Autocracy: a fortnight after it passes the
    event appears, after the overhaul check.
30. **Reform paths (`start_enactment`).** As Persia or the Ottoman Empire with Rationalism: A House of Justice
    (unrest) and Courts for a New Code (strong Intelligentsia or modernizers). Their reform answer starts the
    enactment of Statutory Courts on the spot. If nothing is being enacted afterwards, `start_enactment` doesn't work
    from an event option: fall back to an enactment success bonus for Statutory Courts
    (`country_enactment_success_chance_law_statutory_courts_add`, which needs registering in
    `mod_entity_modifier_types.txt`) and say so in the option's tooltip.
