# Demographics: uploaded minds, a non-biological category — design (owner's calls applied)

> **Status: approved 2026-10-19 (the owner's calls in §7); built 2026-10-19 on `feat/demog-uploaded-minds`**
> (`docs/systems/mod_systems.md` § Uploaded minds; play-test list § Uploaded minds). It answers the
> owner's request of 2026-10-16: "for countries with the Mind Upload Nexus megaproject / Mind Backups tech, explore
> adding a Non-Biological / Uploaded category to the biological age display in the Demographics panel and longevity
> calculations." Parent designs: the late game (`2026-10-11-demographics-late-game-design.md`, cited as
> "late §n") and the census (`2026-10-08-demographics-design.md`). What is built today:
> `docs/systems/mod_systems.md` § Phase 3: the late game. Anything past today is speculation.

## What exists

| Piece | What it does before this build |
|---|---|
| Mind Backups (`mind_backups`, era 12) | Under Full the census carries it as accidents, violence and work deaths −50% for everyone in the state ("the backed-up are restored", late §1.4, call 19); outside Full a flat −5% deaths on the absorbed family. It needs Biological Immortality (`unlocking_technologies`), so every country that has it has stopped ageing for those in care. |
| Mind Upload Nexus (`building_mind_upload_nexus`) | A megaproject unlocked by Mind Backups, up to 5 levels a state, 10,000 staff a level. Outputs digital assets, services, tourism and fine art (£8.1M a level a week at base prices); research speed +5% a level. **No census effect.** |
| Biological Age row | `38 (calendar 61)`: the mean biological age of the state's or country's people beside their calendar age; hover gives the capital's ageing rate and the share in longevity care (`te_dg_elig`). |
| Longevity section | Living to 100, Biological Age, Longevity Care (the share within reach, E) and Longevity Gap (Living to 100, treated less untreated). |
| Biological pyramid | Each cohort's treated part at its biological band, the untreated at the calendar band. |

Nothing in the census tells a person who is backed up from one who isn't, and no one ever stops being biological.

## 1. What an uploaded person is

| Reading | Mechanics | Verdict |
|---|---|---|
| A. Backed up (Mind Backups) | A living person whose mind is saved; if the body dies suddenly, the mind is restored to a new one. | Kept, with call 2's correction (§3). |
| **B. Upload at the end of life** (the Nexus) | A person in longevity care facing death from illness or old age is scanned and goes on as a mind hosted on the Nexus. | **Chosen (call 1).** |
| C. Elective upload | Healthy adults leave their bodies by choice. | Not built. |

B changes the longevity figures without inventing demand: capacity is the Nexus's levels, and the need is the deaths the
census already counts. It makes the megaproject the lever.

## 2. Reading B in the census

**What an upload is (call 6).** The engine's deaths include the uploads: their bodies are gone, so they leave the
engine's pops, and in the census they leave the ring as every death does. The census splits what the engine calls deaths
into true deaths and uploads, and books the uploads into a pool of minds. Uploads are script objects only.

- **Who can upload (call 1).** A person in longevity care in a country with Mind Backups and at least one Nexus level,
  under Full. Human Purity allows none (E is 0); Mandatory Augmentation everyone, within the capacity. No new law terms.
  The census knows the treated parts' deaths by cause (the late sweep counts them at their biological ages), and the share
  of the ever-treated still in care (cover c), so a step's eligible deaths are c × the treated parts' infection and chronic
  deaths, scaled to the step's own deaths by cause.
- **Which deaths (call 4).** Infection and chronic: deaths that come with warning, so there is time to scan. Accidents,
  violence and work stay with Mind Backups' restore; maternal deaths stay deaths.
- **Capacity (call 3).** Country-wide, since minds are hosted on the country's network: 1,000,000 minds a Nexus level,
  summed over its states. The country's census sums the levels at its yearly pulse.
- **The upload share.** The country's census sets the year's share of demand it can host, φ = min(1, free capacity ÷ last
  year's eligible deaths; 1 with none recorded yet). Each state's step books uploads = min(φ × its eligible deaths, the
  capacity still free), and the country's free capacity falls at once, so the year's uploads never pass it, whatever the
  order the states step in. The rest of the eligible die.
- **The pool.** On the country, minds by sex (`te_dg_um_f`, `te_dg_um_m`), archived minds by sex beside them
  (`te_dg_um_af`, `te_dg_um_am`). No ages, no births, no causes of death. **0.1% a year choose to end (call 5)**,
  framed as a choice, not a hardware failure ("chose to end"); it frees capacity. The pool keeps no ages: an upload has a
  calendar age that keeps counting and no body, so it has no band in either pyramid.
- **Against the engine.** The engine has no non-biological pops, and needs none: an upload's body died, and the engine
  counted that death. So the census's people stay the ring and the 150+ pool, which the scale ties to the engine's
  population as before; the uploaded pool sits outside both. The migration residual is the engine's population change
  less the engine's own natural change (the walk's estimate), war dead and kills, so it never reads the ring's deaths or
  the pool and needs no change. Under Full, M still aims at the census's deaths with the uploads in them, so the engine
  goes on killing the bodies.
- **What uploads do (call 6).** They don't work in pops, have no health need, draw no pension, aren't soldiers and aren't
  in the sex balance: none of that reads the pool. Their economic trace is the Nexus's output (§5).
- **A lost Nexus (call 7).** Capacity can fall below the minds hosted (conquest, a downsize). At the next census the
  minds over capacity are **archived (frozen)**, not killed: they don't produce and don't choose to end. When capacity
  returns they are restored before any new uploads (the census restores them first, so the year's free capacity is what
  is left after them).
- **A country that goes.** The pool is the country's variables. A revolution's rebels keep none (the pool's year skips a
  revolutionary country), so a rebel winner holds the nation's pool through the engine's variable merge, and the
  civil war's repair puts its two country modifiers back at once (the winner continues the nation; review of #1070).
  An annexed country's minds go with its variables.

## 3. Mind Backups' restore, scaled by care (call 2)

The −50% on accidents, violence and work applied to everyone in the state, also under Human Purity, where no one is in
care. Reading A says only the backed-up are restored, so the factor becomes `1 − 0.5 × E` (E the state's longevity-care
share): a state with everyone in care keeps today's −50%, and a state with no care gets nothing.

The census read the whole `modifier:state_external_mortality_mult` and `state_work_mortality_mult` totals, so one
carrier's part couldn't be scaled. Mind Backups' two −0.5 lines move to their own census-only types,
`state_backup_external_mortality_mult` and `state_backup_work_mortality_mult` (`demographics_modifier_types.txt`, so a
release strips them), which the census adds × the state's E. The step reads last step's E (the inputs are stored before
eligibility drifts), a year's lag on a figure that moves slowly. Outside Full the flat −5% on the absorbed family stays
as it is (the release precondition).

## 4. The panel

| Row | Where | Shown | Value | Hover |
|---|---|---|---|---|
| **Uploaded Minds** (new) | Longevity, the country | once the country hosts or archives a mind | `4% of people` (minds over minds and people) | minds hosted against capacity (`3.1M of 5M`), uploads and chosen endings last year, the share of eligible deaths that became uploads, archived minds when there are any |
| **Backed Up** (new, call 2) | Longevity | with Mind Backups | `62% of people` (E) | the restore's share of accidents, violence and work deaths |
| Biological Age (changed) | Longevity | as today | `38 (calendar 61)`, over biological people only (the pool was never in the ring) | adds "Uploaded people have no biological age and are left out: N% of our people." when the pool isn't empty |
| Living to 100 (changed) | Longevity | as today | an upload counts as living: the blend's table takes the treated's infection and chronic deaths × (1 − the upload share) | adds the share living to 100 as an upload |
| Deaths per 1,000 (changed) | Overview | as today | true deaths only (deaths less uploads) | adds the uploads per 1,000 |
| Pyramid, biological view | Pyramid | with a pool | a "Non-biological: N women, N men" line under the pyramid | |

Life expectancy reads as today: it is already "100+" by Mind Backups, and an upload counting as living would make it
meaningless. (Since 2026-10-20 the panel shows the figure itself, into the thousands, "over 10,000" past that; the
uploads still don't count in it.) Old age from stays biological: it says when a body is old, and an upload has none. The Causes of Death pie
keeps the uploads in their causes: the bodies did die of them. The state subtab shows the state's own uploads last year
in its Longevity section, since the pool is the country's.

## 5. The Nexus's output under Full (call 6)

- **Throughput follows the minds.** Every Nexus's output scales with the country's utilisation, u = active minds ÷
  capacity. An empty Nexus makes nothing; its inputs scale down with its output, and so does its research speed.
- **The mechanism** follows the Strategic Reserve's: a building-scope static modifier on a good's `_mult` axis, at a
  runtime multiplier. One modifier a good of the method, each at (1 + the building's other bonuses for the good) ×
  (u × its factor − 1), so each good is today's line × u × its factor × (1 + those bonuses): the minds' output takes the
  building's bonuses as any building's would, and an empty Nexus makes nothing whatever lifts its goods (a flat −100%
  alone cancels only the method's own line; review of #1070). The other bonuses are the building's read of the axis less
  the multiplier stored when it was applied. `add_modifier { multiplier = var: }` resolves against ROOT, so the state
  stores each multiplier and its pulse applies them with `multiplier = root.var:`, once a month and when a construction
  site adds a level (a new building).
- **Research speed** is a country line on the production method, which no building modifier reaches: under Full the
  country's census adds −5% × its Nexus levels × their staffing × (1 − u), so the line nets to +5% a level × u.
- **Output per mind** (calibrated in the build from the mod's late production methods; the owner kept it, 2026-10-20: a
  late-game wonder at full capacity that takes years to fill): about £40 a week, between an
  era-12 services worker's few pounds and the top software method's £64 (Self-Improving AI Systems; the era-12 digital
  access method is £115). So a full level, 1,000,000 minds, makes about £40M a week, five times today's £8.1M.
- **Lean toward digital assets**, which are traded; services are local and would flood their own state. A full level:
  digital assets ×15, tourism ×2, fine art ×2, services ×1 (300,000, 40,000, 20,000 and 70,000 units).
- **Inputs** lean toward the traded goods: electronic components and advanced materials ×8, electricity and digital
  access ×2 (both local; a level already burns 30,000 electricity, two and a half fusion plant levels' output).
- **Outside Full** the production method is untouched and the Nexus produces as it does today.

## 6. Outside Full, and Display

Nothing changes outside Full (every census mechanic's rule): the Nexus produces as today, Mind Backups keeps its flat
−5%, and no pool exists. A release comments out Mind Backups' two census-only lines with the census's other types.

**Display shows no pool.** Under Display the census doesn't set the engine's deaths, so the model's infection and chronic
deaths aren't the engine's, and the scale re-ties the ring to the engine's population every step: an upload the model
booked from a death the engine didn't make would stay in the engine's pops, come back into the ring through the scale,
and sit in the pool too. Under Full the engine's deaths are the census's (M), so an upload's body really left. The
residual stays consistent either way (it never reads the pool), but only under Full does the pool count real people.

## 7. Owner calls (answered 2026-10-19)

1. **Reading B**, end-of-life upload hosted by the Nexus, for people in longevity care, with Mind Backups and at least one
   Nexus level.
2. **Mind Backups' restore scales with care**: `1 − 0.5 × E`. Outside Full the flat −5% stays.
3. **Capacity:** 1,000,000 minds a Nexus level, country-wide, summed over its states' levels.
4. **Which deaths:** infection and chronic only.
5. **The pool's loss:** 0.1% a year, minds that choose to end; it frees capacity.
6. **What uploads are:** the engine's deaths split into true deaths and uploads; uploads are only script objects. They
   don't work, need no care, draw no pension, don't fight and aren't in the sex balance. Their trace is the Nexus's
   output: throughput scales with active minds ÷ capacity, output per mind about an era-12 software or services worker's,
   leaning toward digital assets; under Full only.
7. **A lost Nexus:** minds over capacity are archived (frozen), restored before new uploads when capacity returns.
8. **Politics:** the Devout lose approval while the pool is over 1% of people, behind a switch, off by default.

## 8. The build

The model first (`scripts/analysis/demographics_uploads.py`: the pool's year, the upload share, the life tables
counting uploads), with a harness scenario (`demographics_harness.py uploads`: era 11 and era 12 with one and with three
full Nexuses), then the generator's sums, the step's booking, the country's capacity sum and pool, the panel rows, the
Nexus's scaling and the switch, and a test that a country without the Nexus runs exactly as today
(`test_demographics_golden.py` holds).
