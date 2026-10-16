# Demographics: uploaded minds, a non-biological category — design (for the owner's calls)

> **Status: proposal, 2026-10-16.** Nothing here is built. It answers the owner's request of 2026-10-16: "for countries
> with the Mind Upload Nexus megaproject / Mind Backups tech, explore adding a Non-Biological / Uploaded category to the
> biological age display in the Demographics panel and longevity calculations." Parent designs: the late game
> (`2026-10-11-demographics-late-game-design.md`, cited as "late §n") and the census (`2026-10-08-demographics-design.md`).
> What is built today: `docs/systems/mod_systems.md` § Phase 3: the late game. Every number is a starting proposal;
> anything past today is speculation.

## What exists

| Piece | What it does today |
|---|---|
| Mind Backups (`mind_backups`, era 12) | Under Full the census carries it as accidents, violence and work deaths −50% for everyone in the state ("the backed-up are restored", late §1.4, call 19); outside Full a flat −5% deaths on the absorbed family. |
| Mind Upload Nexus (`building_mind_upload_nexus`) | A megaproject unlocked by Mind Backups, up to 5 levels a state, built in any state of a country with the technology. Outputs digital assets, services, tourism and fine art; research speed +5% a level. **No census effect.** |
| Biological Age row | `38 (calendar 61)`: the mean biological age of all the state's or country's people beside their calendar age; hover gives the capital's ageing rate and the share in longevity care (`te_dg_elig`). |
| Longevity section | Longevity Care (the share within reach, E) and Longevity Gap (Living to 100, treated less untreated). |
| Biological pyramid | Each cohort's treated part at its biological band, the untreated at the calendar band. |

Nothing in the census tells a person who is backed up from one who isn't, and no one ever stops being biological.

## 1. What an uploaded person is

Three readings, from the least to the most new machinery:

| Reading | Mechanics | Census change | Verdict |
|---|---|---|---|
| **A. Backed up** (Mind Backups) | A living person whose mind is saved; if the body dies suddenly, the mind is restored to a new one. | The −50% already built; a display line only. | Keep as is, with call 2's correction. |
| **B. Upload at the end of life** (the Nexus) | A person facing death from illness or old age is scanned and goes on as a mind hosted on the Nexus. The death doesn't happen; the person leaves the body. | A pool of uploaded people per state beside the ring; part of the illness and old-age deaths become uploads, within the hosting capacity. | **Proposal.** |
| C. Elective upload | Healthy adults leave their bodies by choice, at some rate a year. | B plus a demand model (who, how many, at what age). | Not proposed: a second speculative rate on top of the first, and it drains the working ages for no reason the game models. |

B is the reading that changes the longevity figures without inventing demand: capacity is the Nexus's levels, and the
need is the deaths the census already counts. It makes the megaproject the lever, which the Nexus lacks today.

## 2. Reading B in the census

- **Who can upload.** A person in longevity care (the state's eligibility E, late §4.2) in a country with Mind Backups
  and at least one Nexus level. Human Purity allows none (its E is 0 already); Mandatory Augmentation everyone within
  the capacity. No new law terms.
- **Which deaths.** Infection and chronic deaths: deaths that come with warning, so there is time to scan. Accidents,
  violence and work stay with Mind Backups' restore; maternal deaths stay too (rare by era 12, and sudden).
- **Capacity.** Country-wide (minds are hosted anywhere on the country's network): `K` minds a Nexus level, summed over
  its states. Proposal `K` = 1,000,000. A country of 100 million at 10 deaths per 1,000 has about 850,000 illness and
  old-age deaths a year; with everyone in care one full Nexus (5 levels, 5 million minds) fills in about six years, so
  building levels is what keeps uploads going. Under immortality deaths are 1.4 per 1,000 and mostly accidents, so
  uploads matter less there than in era 11.
- **The upload share** at a step: `u = E × min(1, free capacity ÷ the country's eligible deaths last year)`. The step
  multiplies each slot's infection and chronic deaths by `1 − u` and books the difference into the state's pool. The
  country's census sums the pools against capacity once a year (the order matters only within a year).
- **The pool.** Per state, people by sex (`te_dg_upf`, `te_dg_upm`): two variables, and only in states that have
  uploaded someone. No ageing, no births, no causes of death; a small loss a year for hardware failure, deletion and
  minds that choose to end (proposal 0.2%, which also frees capacity). The pool keeps no ages: an upload has a calendar
  age that keeps counting and no body, so it has no band in either pyramid.
- **Against the engine.** The engine has no non-biological pops: an uploaded person stays in the pop they were in. So
  the census's people are ring + the 150+ pool + the uploaded pool, and the migration residual (§ The census, "Flows")
  must count all three, or a state with uploads would read them as emigrants. Under Full the step's deaths fall by the
  uploads, so the engine's deaths fall with them and the pops keep the people: the same path every census term takes.
- **What they do.** Proposal, the simplest that holds together: uploaded people count as working-age adults at a
  participation of 0.5 (digital work), have no health need (the Nexus's electricity, electronic components and digital
  access are their upkeep) and draw no pension. They don't count toward fighting-age men or the sex balance.
- **A Nexus that goes.** If the country loses the building or its levels (conquest, a law, a downsize), capacity falls
  below the hosted minds. Proposal: the excess is lost at the next step as deaths (`te_demog_note_kills`' path, so the
  migration residual doesn't read them as emigrants), with a notice. The alternative, a frozen pool that can't grow,
  leaves no reason to defend the Nexus.

## 3. Mind Backups' restore, corrected (a separate call)

The −50% on accidents, violence and work today applies to everyone in the state, also under Human Purity, where no one
is in care, and to people the market hasn't reached. Reading A says only the backed-up are restored. Proposal: the
factor becomes `1 − 0.5 × E` (E the state's longevity-care share), so a state with everyone in care keeps today's −50%
and a state with no care gets nothing. This is one script value in the late-era lines and doesn't need reading B.

## 4. The panel

| Row | Where | Shown | Value | Hover |
|---|---|---|---|---|
| Biological Age (changed) | Overview; state figures | as today | `38 (calendar 61)`, over biological people only | adds "Uploaded people have no biological age and are left out: N% of our people." when the pool isn't empty |
| **Uploaded Minds** (new) | Longevity | once a pool exists | `4% of people` | minds hosted against capacity (`3.1M of 5M`), uploads in the last year, the share of illness and old-age deaths that became uploads, the Nexus levels, the laws |
| Backed Up (new, call 2) | Longevity, Biological Age's hover | with Mind Backups | `62% of people` (E) | the restore's share of accidents, violence and work deaths |
| Living to 100 (changed) | Overview; state figures | as today | an upload counts as living: the life tables take infection and chronic deaths × (1 − u) | adds the share living to 100 as an upload |
| Pyramid, biological view | Overview | with a pool | a "Non-biological: N" line under the pyramid, women and men | |

Old age from stays biological: it says when a body is old, and an upload has none. Life expectancy reads as today
(it is already "100+" by then).

## 5. Cost

Two variables a state with uploads, two on the country (capacity, last year's eligible deaths), and per slot one
multiply on two causes the sweep already computes. The life tables' change is the same multiply. Against about 450 a
treated state today, it is under 1%. No new engine facts: the wonder effects already read a building's level as
`b:building_<wonder>.level` (`generic_wonder_construction_base`), and E is stored.

## 6. Outside Full

Nothing changes (every census mechanic's rule). Under Display only the panel shows the pool and the figures; births and
deaths don't move. A release comments the inputs out with the census's other types if any new type carries them (none
proposed: capacity reads the building directly).

## 7. Owner calls

1. **Reading B, end-of-life upload hosted by the Nexus** (proposal), against display only (show A's backed-up share
   and stop there) or C.
2. **Mind Backups' restore scaled by longevity care** (`1 − 0.5 × E`, §3), against today's −50% for everyone.
3. **Capacity:** 1,000,000 minds a Nexus level, country-wide.
4. **Which deaths can upload:** infection and chronic.
5. **The pool's loss:** 0.2% a year.
6. **What uploaded people do:** working adults at 0.5 participation, no health need, no pension; not soldiers.
7. **A lost Nexus:** the minds over capacity die, with a notice.
8. **Politics (optional, off by default like the gap's were):** the Devout lose approval while the pool is over 1% of
   people, as Human Purity's supporters would. Proposal: build it behind a switch, sized after a play-test.

## 8. If approved: the build

The model first (`demographics_model.py`: the pool, the upload share, the life tables), with a harness scenario
(`demographics_harness.py lategame`: era 11 with one and with three full Nexuses), then the generator's slot change and
the pool's step, the country's capacity sum, the panel rows, and a test that a country without the Nexus runs exactly
as today (`test_demographics_golden.py` holds).
