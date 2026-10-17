# Demographics in the late game: old age, work, children and who lives longest — design (approved)

> **Built 2026-10-12** (branch `feat/demog-p3-late-game`, from this spec with no plan document, owner's process of that
> day): `docs/systems/mod_systems.md` § Phase 3: the late game says what shipped and where it settles what this design
> left open (the postponement shift held at 0; `autonomous_vehicles` not built (since 2026-10-16 a modern-safety carrier instead); the gap's politics behind a switch, off;
> the harness's `lategame` results against the sketched figures). The design below is unchanged.
>
> **2026-10-16 (owner):** the gap's politics are on at call 15's sizes, and the play-test checks them rather than sizing
> them first. As built (#947) the approval multiplier is the gap × the share of all the country's people not in care, not
> the lower strata's untreated share (milder where the market reaches the rich first), and the labor line is
> `state_pop_support_movement_labor_mult` at +10% × the state's gap, not the `_add` §4.4 names. §1.4's adult-mortality check is answered for men by a modern-safety factor on work and accidents and violence
> (era 7-9 technologies; `docs/systems/mod_systems.md` § Causes of Death); women's excess is adult infection and chronic
> deaths, left until the AI's insolvency (#933) is fixed.
>
> **Status: approved design, 2026-10-11.** The owner approved every call in §9 as recommended the same day; call 15 (the
> gap's politics) waits for a play-test and call 16's B for a fit. It was revised after an independent review the same
> day (who is treated is now tracked per band, §1.2–§1.3). It answers the owner's request of 2026-10-11: scope the late
> game's demography as one model before phase 2's workforce, pension and health work bakes in early-game assumptions.
> Parent spec: `2026-10-08-demographics-design.md` (cited as "parent §n"); this design amends its §1 ("Ages past 95 and
> the late eras"), design rule 3, §7, §8.2, §8.3, §10 and §13 ("Fertility without ageing") where it says so. It builds
> on #894's rulings (workforce from participation; who pays for the old) and on two plans in flight: Causes of Death
> (draft PR #905, branch `feat/demog-causes-of-death`) and Late Marriage and Birth Spacing (draft PR #906). No code
> here. Every number is a starting proposal for the harness. Figures marked *sketch* come from a throwaway Python run of
> the census's own model (`demographics_model.py`, the harness's Rich-today inputs) extended with a biological clock;
> they are the model's arithmetic, not history. Anything past today is speculation, marked as such.

## Context

**The request** (owner, 2026-10-11): "Late game has a lot of demographic considerations not present in earlier eras —
how does retirement work when 'old age' is delayed, how many children do women have and when, does access to life
extension come to the rich earlier, how is all this displayed, etc."

**What exists.**
- The census (parent §1–§3, built): one-year cohorts to 150 plus a pool, five causes of death, fertility as wealth ×
  natural × (1 − means × (1 − desired)), and from phase 2 step 4 the census's births and deaths term M under Full.
- The parent's late-era answer (§1): biological age from `personalized_medicine`, one extra variable per slot, read by
  "every age-specific rate"; Biological Immortality stops ageing and winds it back toward 35; a calendar/biological
  pyramid toggle. §13 adds the open question that an immortal woman's lifetime births have no limit, and proposes a
  per-cohort children-so-far count to bound them.
- #894's rulings: workforce from participation (men at a bit under all, women from about 0 to about men's by the
  women's-rights laws, higher in the lower strata; bounded by schooling below and pensions above); pensions cost
  money and health care bureaucracy; **don't hard-code 65**; growth matters more than exact children per woman; drift
  toward targets over jumps.
- The late-era content, as the game files have it today:

| Carrier | What it does now | File |
|---|---|---|
| `mrna_therapeutics` (era 10) | a Ministry of Health level; the Biologics and mRNA production method. Nothing slows ageing yet | `era_10.txt:127` |
| `telemedicine` (era 10) | chronic treatment +0.2 | `era_10.txt:315` |
| `mental_health_awareness` (era 10) | deaths −5%, added on top of the census | `era_10.txt:362` |
| `personalized_medicine` (era 11) | chronic treatment +0.2. Nothing slows ageing yet | `era_11.txt:373` |
| `biological_immortality` (era 12) | deaths −20% on top, `character_health_add` | `era_12.txt:268` |
| `mind_backups` (era 12) | deaths −5% on top | `era_12.txt:341` |
| The augmentation laws | chronic treatment +0.05 to +0.10; Unrestricted gives the upper strata SoL +5 and the lower −1 | `extra_laws.txt:1658-1820` |
| Ectogenesis, Cloning Vats (State Youth Centers) | births +25% and +100% per level, on top | `extra_pms.txt:18742`, `:18774` |
| Continuity of title (inheritance event .6) | under immortality, Wealth Concentration's target is pinned at the score | `inheritance_events.txt:417` |

The three era-10 to era-12 lines sit in `ENGINE_LINES_ON_TOP` (`demographics_params.py:263`) with the note "revisit
with step 6". The game ends on 1 January 2136 (`extra_defines.txt:153`); the tech audit places era 11 at about
2030–2060 and era 12 from 2060 (`docs/audits/tech_era_appropriateness_audit.md:16-17`). So immortality has between a
few and seventy years to play out, and the pool at 150 does fill: 1.3% of people by the game's end if immortality
comes in 2080, about 14% if it comes in 2056 (§1.4).

**The risk the owner named.** Phase 2 is about to write the workforce effect (ages 15–64, an over-65 share), the
pension bill (a 65+ count) and the health bill (a 65+ share). Each would be wrong by the late game: 65 stops meaning
old, the 15–64 band stops meaning working, and a 65+ count stops measuring need. This design fixes the interfaces now
and leaves the late mechanics for phase 3.

### What the census's own arithmetic says (sketch)

Life tables from the harness's Rich-today inputs (Public Health Insurance at level 8, medicine to era 10, SoL 40),
both sexes' mean. "Ageing 0.75" means the treated age three-quarters of a year each year from 25.

| Case | Life expectancy | At 65 | Living to 100 | Old age from (15 years left), women / men |
|---|---|---|---|---|
| Britain 1836 | 39.8 | 12.5 | about 0 | 63 / 60 |
| Rich today | 77.5 | 21.7 | 9% | 77 / 73 |
| … and ageing 0.9 (era 10) | 82.2 | 26.8 | 23% | 84 / 81 |
| Era 11 medicine and Medical Augmentation (chronic ×0.16) | 88.1 | 31.7 | 35% | 92 / 86 |
| … and ageing 0.75 | 103 | 49 | 67% | 117 / 110 |
| … and ageing 0.5 | 130 (122 to 150) | 79 | 78% | 165 / 156 |
| Immortality: the body held at 35 | 559 (129 to 150) | 553 | 81% | never |

- **The census's life expectancy stops at 150** (its life table runs over the ring's groups,
  `demographics_model.py:131`), so under immortality the panel would read 129 for a figure of 559. Both mislead (§6).
- **Under immortality the deaths left are mostly work, accidents and violence.** Living to 100 stops at 81% because
  the model's death rates at 35 run on: about 120 per 100,000 a year for women and 360 for men, three-fifths and
  four-fifths of it work, accidents and violence. Women's median age at death is 594 and men's 203. Those schedules
  were fitted to the 19th century; late, they are the whole death rate (§1.4).

One rich state from today's stable structure at 1.6 children per woman, 60 years on (calendar fertility timing;
everyone treated in the slowing and immortality rows, §1.3 for partial care; "workforce" is the share of all people at
work under modern women's participation and §2.1's capacity table, with a pension at 65 or none):

| Case | People at 30 / 60 years | Deaths per 1,000 at 30 | Calendar 65+ at 60 | Mean biological age | Health need (1836 = 0.97) | Workforce at 60: pension 65 / none |
|---|---|---|---|---|---|---|
| No change | 0.75 / 0.56 | 17.9 | 31% | 48 | 1.71 | 0.45 / 0.55 |
| Era 11 medicine, no slowing | 0.88 / 0.68 | 14.6 | 42% | 56 | 2.11 | 0.38 / 0.49 |
| Era 10, ageing 0.9 | 0.77 / 0.61 | 16.6 | 36% | 48 | 1.68 | 0.43 / 0.57 |
| Era 10 (0.9) for 20 years, then era 11 (0.75) | 0.84 / 0.75 | 8.9 | 48% | 53 | 1.88 | 0.36 / 0.55 |
| Ageing 0.5 | 0.97 / 0.90 | 8.6 | 56% | 50 | 1.69 | 0.33 / 0.61 |
| Immortality, pulled 3% a year toward 35 | 1.10 / 1.19 | 2.4 | 67% | 31 | 0.79 | 0.29 / 0.77 |

Three things fall out, and the rest of the design is built on them:
1. **Medicine that treats without slowing ageing makes a society older and sicker** (health need 1.73 → 2.11). Only
   slowing the clock relieves it. That is the owner's "medical tech moderately raises health cost", with a reason and
   an end (§5.2).
2. **A pension at calendar 65 under immortality makes two-thirds of the people pensioners**, and the workforce falls
   to 0.29 against 0.77 with no retirement. The pension age must be able to follow longevity (§2.2).
3. **Whether immortality is a population shock depends on which clock fertility reads** (§3.3): ×1.17 in 50 years when
   families are timed by calendar age, ×1.86 and rising when fertility reads biological age with no bound.
4. **Who is treated must be tracked per band, not as one state share** (§1.3): a single share applied to every cohort
   each year kills half again as many as tracking does when half the state is treated.

## Rulings this design keeps

| Ruling | Source |
|---|---|
| Nothing changes outside Full; Display only shows what Full would do | owner, 2026-10-10 |
| General mechanisms, no country- or culture-specific mechanics; asymmetric outcomes through shared mechanics, never `is_ai` | owner; memory |
| Workforce from participation; working-age share × share at work = workforce on the panel | #894 |
| Pensions cost money, health care costs bureaucracy; medical technology moderately raises the health cost; no hard-coded 65 | #894 |
| Growth matters more than exact children per woman; drift over jumps | #894 |
| Pension age as a setting under Old Age Pension, not amendments. The parent's three positions stand; two linked positions are added (§2.2; owner, 2026-10-11: offer both) | parent Decisions |
| Calendar/biological toggle on the pyramid from era 11; ring to about 150 from 1836 | parent Decisions |
| Measures are GUI buttons, national for now | parent Decisions |
| One-year cohorts at about 26 MB of an 1836 plain-text save | #894 |
| Both linked pension variants are offered; the setting lives on the Demographics tab as buttons, under Old Age Pension only | owner, 2026-10-11 (§2.2) |
| A small ageing step at era 10: rate 0.9 | owner, 2026-10-11 (§1.2) |
| The workforce ratio is uncapped; watch it in the harness and an observer run | owner, 2026-10-11 (§2.1) |
| Conscription's age-structure term falls as far as the pool does, to −1; the +0.25 ceiling stays for now | owner, 2026-10-11 (§2.5) |
| Vanilla Old Age Pension's +20% dependents' income has no treasury cost | owner, 2026-10-11 (§5.1) |
| Every call in §9 as recommended; call 15 play-test later, call 16's B fit later | owner, 2026-10-11 (§9) |

## 0. The architecture: two clocks, one sweep

**Every age-specific table in the census is read through an age index.** Today there is one: the sweep visits the ring
in age order and enters each rate group when the rate age reaches the next group's start
(`te_demog_effects.txt:1116-1121`, `te_demog_enter_group` in the generated effects). The late game adds a second index,
biological age, and changes nothing else about how a table is read.

**Each rule names its clock.** The test: does the rule follow the body, or law and custom?

| Rule | Clock | Why |
|---|---|---|
| The five causes of death | biological | the body dies; accidents' and violence's schedules too, since the young-adult peak and the old-age falls both follow the body |
| Ability to work (capacity) | biological | frailty, not the calendar, ends work without a pension |
| Health need | biological | care follows illness |
| Unplanned births (the share the means don't reach) | biological | they follow fecundity |
| Planned births (the wanted family) | calendar for their timing, biological for whether the body allows them | families form at a stage of life; a postponed birth needs a fertile body (§3.2) |
| Pension eligibility | calendar | the law reads a birth date |
| Schooling and child labour (the working ages' lower bound) | calendar | law |
| Conscription and the war dead | both: a calendar floor (legal adulthood, 20) and a biological ceiling (fitness, 39) | the law says who may be called, the body who is fit to serve (§2.5) |
| Youth bulge (20–29), migrant classes | calendar | life stage |
| Marriage (Late Marriage's share) | calendar | custom |

**Before life extension the two clocks are the same**, so phase 2 can build every rule against its named clock at no
cost: the biological index is the calendar index until a state has a treated share (§1.2). That indirection is the one
thing phase 2 must build now (§8.1).

**Alternative considered: the parent's single clock** ("every age-specific rate reads biological age"). It makes an
immortal woman bear children at the age-35 rate for ever (parent §13) and makes the pension law read the body. Pension
law and family formation are social, so they get the social clock.

## 1. What "old" means

### 1.1 Two kinds of medicine

- **Treatment** lowers the risk of death at a given biological age. That is all medicine in eras 1–10: the census's
  `1 − access × treatment` (Causes of Death plan). It already delays death: chronic mortality doubles about every 8
  years of age (Gompertz; `demographics_params.py:58-64`), so a chronic multiplier m equals a delay of 8 × log2(1/m)
  years. Today's ×0.40 is about 10.5 years; era 11's ×0.16 about 21. But it delays only death. People still tire at 65,
  stop bearing children at 45 and need care for longer: medicine without slowing is the "expansion of morbidity"
  (Gruenberg 1977) against Fries's "compression" (1980), and the sketch's health need rises.
- **Life extension** slows the clock itself, so death, frailty, menopause and need all move together. Nothing in the
  game does it yet. Real evidence stops at animals: rapamycin started late extended mice's lives by about 9–14%
  (Harrison et al. 2009, *Nature*); no intervention has slowed human ageing. Everything from era 10's step here is
  speculation, placed so that era 10 is a small step, era 11 a larger one and era 12 the leap.

### 1.2 Biological age: who is treated, and how fast they age

**Three state figures:**
- **Eligibility E** (0–1): the share of the state's people within reach of longevity care (§4.2), from the wealth
  bands and the laws. It drifts toward that target at the Causes of Death plan's medical-diffusion rate (0.1 +
  `state_medical_diffusion_add` of the gap a year), both ways: care rolls out, and a ban phases it out as clinics
  close.
- **The ageing rate r** of those in care: biological years per calendar year. 1 until the first carrier; read from a
  new script-only state type, `state_ageing_rate_add` (negative), as the census reads its other types.
- **Cover c** (0–1): the share of everyone ever treated who is still in care. 1 normally; when E falls, c falls in
  proportion.

**Two figures per five-year birth band**, adults only (children are not slowed; a cohort reaching 25 joins at the
state's E):
- **The treated share s**: the share of the band's people who have been in care.
- **The deficit d**: their mean calendar age − biological age. The untreated are at their calendar age.

**Each year, per band:**
1. **Deaths**: the treated part at its biological age, the rest at its calendar age (§1.3).
2. **Selection**: s becomes the treated survivors ÷ all survivors. The untreated die faster, so the old become more
   treated, as the rich already are among the very old.
3. **Ageing**: d += c × (1 − r), plus the pull under immortality × c (§1.4). Bodies out of care age at 1 from where
   they are. They never snap back to their calendar age (#894: drift over jumps).
4. **Joining**: when E rises, cover returns first; past that, the same share of every band's untreated joins with no
   deficit, so d × s_old ÷ s_new.
5. **Migrants**: emigrants leave with their band's mix. Immigrants are the census's residual and have no known origin,
   so they join at the destination's mix: care follows where people live. Internal Resettlement's moves are in the
   residual too: its effects read no census variable today (`resettlement_effects.txt`), and parent §12 leaves them
   there until phase 3. **Decided: leave them there** (owner, 2026-10-11). Within one country the laws are the same and
   only wealth differs, so the error is small. Carrying the origin's share and deficit would be new phase-3 work, worth
   adding only if phase 3 builds the parent's resettlement profiles, which need the same hook.

**The pool** (150+) keeps a share and a deficit like its mean age. **A state seeded once ageing is slowed** (a new or
split state) starts each band at s = E and d = (1 − r) × (calendar − 25), the steady state of its current rate.

**Carriers (proposal; speculation):**

| Carrier | Era | `state_ageing_rate_add` | Why |
|---|---|---|---|
| `mrna_therapeutics` | 10 | −0.10 | biologics such as senolytics, which clear senescent cells (first human trial: Justice et al. 2019, *EBioMedicine*), and mRNA-delivered therapies; of the mod's two era-10 medical technologies, the one that acts on the body (`telemedicine` is how care reaches it) |
| `personalized_medicine` | 11 | −0.10 | geroprotective drugs (the rapamycin class), dosed to the person |
| `genetic_engineering` | 11 | −0.05 | gene therapies against the hallmarks of ageing |
| `synthetic_biology` | 11 | −0.05 (since 2026-10-16) | engineered cells that repair their own damage |
| `biological_immortality` | 12 | −0.70 (r = 0; −0.75 until 2026-10-16) and `state_rejuvenation_add` +0.03 | ageing stops; the body winds back |

The ladder (owner, 2026-10-11) is r = 0.9 at era 10, 0.75 at era 11, then 0. At 0.9 a treated person's steady-state
life expectancy is about 82, against 77.5 untreated with the same medicine (sketch). At 0.75 it is about 103, near the
optimistic end of extrapolations (best-practice life expectancy has risen about three months a year since 1840, Oeppen
and Vaupel 2002, *Science*; against that, Olshansky et al. 2024, *Nature Aging*, argue radical extension this century
is implausible). The parent proposed about half a year a year at era 11 (r = 0.5); that gives 130 and an old-age
threshold past the ring (§9, call 3).

### 1.3 How the ring carries it

The sweep reads each slot's rates twice: the untreated part's at its calendar index (the running pointer, as now) and
the treated part's at its biological index. The second is a lookup: precompute each group's rates once per step (31
groups, two sexes, as locals), then take a slot's treated rates by a generated five-comparison tree on its biological
age (the form `te_demog_enter_group` already has). Treated and untreated die apart, not at a blended rate, because
deaths are convex in age: on women's chronic base, half a cohort at 60 and half at 90 die at (1,700 + 22,000) ÷ 2 per
100,000, not at 75's 6,200.

**Who is treated: the first draft's rule was wrong** (independent review, 2026-10-11). It kept one state share A and
gave each cohort, every year, deaths = A × the treated rate + (1 − A) × the calendar rate. That draws the untreated
share afresh from survivors who are by then mostly treated, so it kills too many. Tracked per cohort (treated,
formerly treated and untreated apart) against the rules, year 50, era 11's rates, immortality pulled 3% a year
(sketch; the shares are each cohort's at onset and of the newborn, and rise by selection):

| Case | Truth: deaths per 1,000, people | First draft | Share and deficit per band | One deficit per band |
|---|---|---|---|---|
| Immortality, 20% treated | 12.0, ×0.83 | 14.4, ×0.78 | 12.0, ×0.82 | 8.6, ×0.92 |
| Immortality, 50% treated | 7.6, ×0.95 | 11.4, ×0.88 | 7.5, ×0.95 | 3.3, ×1.09 |
| Immortality, 90% treated | 3.1, ×1.13 | 4.6, ×1.09 | 3.1, ×1.13 | 2.3, ×1.16 |
| Rich-first: eligible 0 → 60% over 40 years | 6.9, ×0.90 | 9.7, ×0.87 | 7.0, ×0.90 | 4.0, ×0.96 |
| Era 11 (r 0.75), 50% treated | 13.7, ×0.79 | 14.0, ×0.78 | 13.7, ×0.79 | 13.6, ×0.79 |
| Everyone treated for 50 years, then a ban | 2.2 → 2.4 over five years | 42.6 the next year | 2.2 → 2.3 | 2.2 → 2.4 |

- **A share and a deficit per band** (decided) tracks the truth within 0.1 per 1,000 in every case. The ring's
  treated and untreated parts die at the rates of §4.3's two life tables, so the longevity gap the panel shows is the
  gap the ring has.
- **One deficit per band over the whole cohort**, growing by E × (1 − r) (the review's simpler alternative), has no
  selection error and no snap-back, and is right under era 11's slowing. Under immortality with partial access it makes
  every member of a half-treated cohort half-immortal: deaths at less than half the truth, and a population that should
  shrink (×0.95) grows (×1.09). It also leaves the ring with no treated and untreated parts, so the gap becomes display
  only.
- The ban row is the rule above: bodies keep their age. The first draft put the formerly treated back at their
  calendar age at once.

**Storage** (each from era 10's step only, in states with someone treated):

| Option | Variables a state | Fit | Save, full late game |
|---|---|---|---|
| **Share and deficit per five-year birth band** (decided) | up to 50, the pool's 2, E and c | the truth within 0.1 per 1,000 (table above) | about 3.4 MB |
| One deficit per band | up to 25 and the pool's | wrong under immortality with partial access (table above) | about 1.7 MB |
| Share and deficit per slot | up to 250 | exact | about 15 MB |

Bands are birth year ÷ 5 mod 30, which nests in the ring's 150 slots; the display bands are five years anyway. A band's
five cohorts sit within ±2 years of each other, which the table's runs include.

### 1.4 Biological Immortality

- **Ageing stops** (r = 0) for the treated, and the body winds back: each year a treated cohort above 35 closes a share
  of the gap to 35 (`state_rejuvenation_add`).
- **The pull is a drift, not a jump** (#894 (d)). At 3% a year the gap halves in 23 years and deaths per 1,000 fall
  from 8.2 to 3.6 in ten years and 2.7 in twenty; at 10% they fall to 2.4 in ten. Proposal: 3%.
- **What kills people afterwards**: work, accidents and violence (three-fifths of women's remaining deaths and
  four-fifths of men's in the sketch), the infection floor and chronic disease at 35's rate. So the late-era levers
  that matter are the external and work ones. Two follow from carriers the game already has:
  - `mental_health_awareness`: external causes −10% (suicide is a large share of young adults' external deaths), in
    place of its flat −5% on top;
  - `mind_backups`: external and work deaths −50% (the backed-up are restored; speculation), in place of its −5% on
    top.
  A third is a proposal: `autonomous_vehicles` external −10% (traffic deaths).
- **The model's adult external and work schedules need a late check.** They were fitted to 1836–1900; the sketch's
  immortal men die at about 0.36% a year, so their median age at death is 203 against women's 594. A harness band for
  2000–2020 adult mortality (15–49) is phase 3's first task.
- **`biological_immortality`'s −20% on top moves into the census under Full** (it is the ageing rate now); outside
  Full it stays as the flat line. The same for the other two lines above (§8.4).
- **The pool at 150 fills** (sketch, everyone treated, 3% pull): 0.4% of people after 50 years of immortality, 1.3%
  after 56 (immortality in 2080 and the game's end), 14% after 80 (immortality in 2056). It keeps its mean age, share
  and deficit, so its deaths stay right; the calendar pyramid's top bar reads 150+.

### 1.5 Old age from: the old-age threshold

- **"Old" as a number**: the age at which a state's people have 15 years of life left on average, Sanderson and
  Scherbov's prospective old-age threshold (2005, *Nature*; 2010, *Science*).
- **Its values** (sketch, women / men): 63 / 60 in 1836, 66 / 63 in 1950, 77 / 73 today, 84 / 81 with era 10's 0.9,
  92 / 86 with era 11
  medicine, 117 / 110 with ageing at 0.75. Under immortality there is none: no age has only 15 years left.
- **How**: from the census's own life table, a reverse pass over its 31 groups at each step, with the death rates at
  each age blended by the ring's own treated share at that age (§1.2's s); women and men averaged. A period figure,
  like life expectancy. Averaging the two tables' remaining lives by the treated share instead would lose the
  threshold once a few percent are immortal.
- **With some of a state treated** (era 11 rates, immortality, a constant share at every age; review's check): the
  untreated alone give 92 / 86; a fifth treated gives 99 / 91; half gives none. Selection makes the old the most
  treated, so the ring's own blend reaches none sooner. The census keeps both figures: the state's blend (Linked to
  Average Longevity follows it) and the untreated's alone (Linked to Common Longevity follows it).
- **What reads it**: the panel's Old age from row; the two linked pension positions (§2.2); the after-pension share
  under UBI and Post-Scarcity (§2.2); events that mean "the old". Deaths, capacity and health need don't: they read
  biological age directly.

## 2. Work and retirement

### 2.1 Participation by age, with both clocks

For each cohort and sex, the census counts workers as people × participation, where

    participation = working-age start (calendar) × [below the pension age (calendar) ? 1 : after-pension share]
                    × capacity (biological) × the sex's rate

- **The sex's rate** is #894's: men a bit under all (proposal 0.92); women from about 0 to about men's by the
  women's-rights laws, higher in the lower strata, entering through the state's class mix.
- **The working-age start** is #894's lower bound: schooling and child labour (Child Labor Allowed lets the 10–14s
  work at 0.3, Restricted 0.1, Compulsory Primary School 0; parent §7). Late eras may push it towards 20 as tertiary
  schooling spreads; not proposed now.
- **Capacity by biological age** (proposal; the harness fits it): 1 to 59, 0.95 at 60–64, 0.85 at 65–69, 0.7 at 70–74,
  0.5 at 75–79, 0.3 at 80–84, 0.1 from 85. With no pension this is the only upper bound: people work until they can't.
  Anchor: about three-quarters of American men over 65 were in the labour force in 1880 (Costa 1998, *The Evolution of
  Retirement*, as summarised; *unverified*), and parent §8.2's "about a fifth today".
- **The after-pension share** is the share of the eligible who keep working: 0.15 (proposal), times capacity.

**So the upper bound is whichever comes first**: the body (capacity) or the law (the pension age). Life extension
moves the first and leaves the second, so in the late game the pension setting decides the workforce.

**The panel's figure** (#894): working-age share × share at work = workforce, where the working ages run from the
working-age start to the pension age (to capacity's end without a pension), and the share at work is workers ÷ those
people. Workers past the pension age count in the numerator; the hover lists them.

**Into the engine**: the state's workforce ratio heads toward this fraction through `state_working_adult_ratio_add`
(`modifiers.log:2007`), scaled so a typical 1836 state lands on vanilla's 0.25 (#894).

**The target is a total, as M is for births and deaths.** About twenty other lines already move the ratio. The
census's term is the target less the pops' own base ratios (people-weighted, from the walk: aristocrats 0.2, slaves
0.5, the rest 0.25) less the lines left on top. Two families, by the moved lines' pattern (script-only types the mod
applies outside Full and the census models under Full):
- **Carried by the participation model**, so cancelled under Full: women's work (the five women's-rights laws, +0.05
  to +0.3; State-Sponsored Family Planning +0.05; Communal Child-Rearing +0.1; the Pill +0.05; second-wave feminism
  and personal appliances +0.025 each), which set the women's rate, the "maybe technology" of #894; and retirement
  (Old Age Pension −0.01 a level, UBI −0.02, Post-Scarcity −0.04 (since dropped in every game: phase 2 call 1,
  2026-10-12), Pro-Natalist's −0.05, which parent §8.1 already
  drops), which the pension age replaces. Without this, women's work would count twice.
- **Left on top**: the criminal-justice laws, the Ministries of Labour, State Eugenics, Community Service and
  Mandatory Minimums, the failed-state modifier, and one company's and one production method's lines.

This amends the parent's rule 3 ("ones that stand for women's or children's work stay"): under Full, women's work is
the participation model's, and those lines set it.

**The engine's scale.** Under immortality the sketch's workforce reaches 0.66 of all people with Linked to Average
Longevity, 0.39 with Linked to Common and 0.77 with no pension (§2.3), against today's 0.45: about 0.62, 0.36 and 0.73
on the engine's scale, against vanilla's 0.25 in 1836 and about 0.42 today. **No cap** (owner, 2026-10-11): the
harness and an observer run watch the engine-scale figures (about 0.62 under Linked to Average, 0.73 with no pension),
and a cap comes only if they show a problem (§9, call 10).

### 2.2 The pension age

**The pension age is one number per country**, stored as a variable (a revolution's winner keeps it; CLAUDE.md, "the
winner continues the nation"), read by the workforce (§2.1), the pension bill (§5.1) and the panel. The setting under
Old Age Pension has five positions (owner, 2026-10-11: both linked variants are offered, so the player chooses who
bears the cost):

| Position | Pension age | Trade-off | Interest groups (approval while in force; proposal) |
|---|---|---|---|
| **Early Retirement** | 60 | frees jobs for the young (parent §8.2); the largest bill | Trade Unions +2; Industrialists −1 |
| **Standard** | 65 | the default; grows more generous as lives lengthen | none |
| **Raised Pension Age** | 70 | a smaller bill; the old work longer | Trade Unions −2, Rural Folk −1; Industrialists +1 |
| **Linked to Average Longevity** (new) | five years below the state's old-age threshold (§1.5: death rates blended at each age by the treated share) | the cheapest under life extension, but the untreated, who still age, may never reach it once enough of the state is treated | Trade Unions −1, Rural Folk −1; Industrialists +1 |
| **Linked to Common Longevity** (new) | five years below the untreated's old-age threshold (§1.5) | fairer: the age follows those who still age; but the treated draw a pension from about 84 for ever, and that bill is the price | Trade Unions +1, Rural Folk +1; Industrialists −1 |

- **Both linked positions** are at least 65 and move at most a year a year. The floor brings back a fixed age on
  purpose: it makes linking a reform that only raises the age (§9, call 6). Before anyone is treated they give the
  same age: 65 (the floor) in 1836 and 1950, 70 today, about 84 with era 11 medicine (about 78 at era 10's 0.9 with
  everyone treated, about 108 at era 11's 0.75). They part once some of a state
  is treated.
- **Existing pensioners keep their pensions.** The age moves at most a year a year and every cohort ages a year a
  year, so no one already over it falls below it.
- **Why linked positions, and why two.** Indexing every position would remove the 20th century's fiscal squeeze: a
  fixed 65 that grows more generous as lives lengthen *is* the history (Germany's 70 in 1889, 65 from 1916; 65 held
  for most of a century while life at 65 grew by about eight years). Linking is the early-21st-century reform: Denmark
  linked its pension age to life expectancy in 2006 and has legislated 70 by 2040 (as summarised; *unverified*).
  Denmark's rule reads the national average, and the average is regressive: raising the eligibility age cuts low
  earners' lifetime benefits most, since their lives are shorter (US National Academies, *The Growing Gap in Life
  Expectancy by Income*, 2015, as summarised). Once life extension reaches the rich first, that choice is the late
  game's pension question, so the player gets both answers.
- **The minimum term** stays five years for every position (parent §8.2).
- **Where it lives** (owner, 2026-10-11: the panel, not a law or a journal entry): five buttons in the Work and
  Retirement section of the Demographics tab (Population panel → Demographics), beside the pension age (style guide
  rule 6). They show only under Old Age Pension. A button that can't be pressed is greyed with its reason in the
  tooltip: the five-year term still running, with the year it ends. Under Display only the setting changes nothing,
  so the buttons are greyed with that reason ("Pension settings act only under the Full Demographics rule") rather
  than hidden: Display only shows what Full would do, and no button looks live. Under Disabled the tab is gone, which
  is fine, since every effect is Full's.
- **AI weights** (shared mechanics, the same for every country, never `is_ai`), applied by the AI's yearly country
  pulse: the bill's share of GDP and a weak treasury push toward Raised and Linked to Average; a wide longevity gap
  (§4.3) pushes toward Linked to Common, as the country's unions would; a youth-bulge or unemployment problem pushes
  toward Early. The five-year term binds the AI as it binds the player.
- **UBI and Post-Scarcity**, the welfare group's later laws (`extra_laws.txt:285`, `:344`), replace Old Age Pension.
  Under them there is no pension age: the old are paid as everyone is, there is no separate pension bill, and the
  working ages end at capacity, with the after-pension share applied from the old-age threshold (§1.5's figure) as a
  stand-in for choosing leisure. Post-Scarcity's own −0.04 workforce line is dropped in every game (owner,
  2026-10-12: phase 2 spec §13 call 1, #925).
- **Events** that read "65+" (the parent's Greying of the Nation) read the pension age or the old-age threshold
  instead. Two late ones: **The Pension Without End** (pensioners pass half the people: link it, raise it or pay) and
  **The Last Generation?** (Biological Immortality; parent §9).

### 2.3 What an immortal society's workforce looks like

Sketch: one rich state 30 and 60 years after immortality, everyone treated, the 3% pull, 1.6 children per woman, B
= 0.4 (§5.1). Each position starts from today's 70 where it rises.

| Position | Pension age | Pensioners at 30 / 60 years | Bill, % of GDP | Workforce |
|---|---|---|---|---|
| Early (60) | 60 | 57% / 70% | 23 / 28 | 0.33 / 0.27 |
| Standard (65) | 65 | 53% / 67% | 21 / 27 | 0.37 / 0.29 |
| Raised (70) | 70 | 48% / 63% | 19 / 25 | 0.40 / 0.32 |
| Linked to Common Longevity | 84 from year 14 | 34% / 54% | 14 / 21 | 0.50 / 0.39 |
| Linked to Average Longevity | rising a year a year (the threshold is gone) | 18% / 16% | 7 / 6 | 0.61 / 0.66 |
| No Old Age Pension | none | 0 | 0 | 0.74 / 0.77 |

- **Linked to Average**: those already retired when immortality came keep their pensions for good; nobody younger
  reaches the age. Cheap, and with some of the state untreated, it is they who never retire.
- **Linked to Common**: everyone who reaches 84 retires for good, treated or not, so the pensioners grow as the
  immortal pile up past it. Fairer to the untreated, at a bill near Standard's within two generations.
- **Standard (65)**: a leisure society paid for by a quarter of its people; it can be a choice, and Post-Scarcity is
  where the game puts it.
- **Without Old Age Pension**: the old never tire.

### 2.4 Youth and dependency

The youth share falls under immortality as the adults pile up (the calendar 0–14 share is about half today's after
60 years). The youth bulge (calendar 20–29) disappears. Dependency becomes a choice made through the pension age, not a
fact of biology: exactly the parent's "ageing is mainly a fiscal problem", taken to its end.

### 2.5 Conscription and the war dead

Conscription could read either clock (owner, 2026-10-11). Parent §7 sets `state_conscription_rate_mult` from men aged
20–39 against the 1836 reference, capped at ±0.25. The war dead (parent §2.5) come from men aged 18–40 by rate age, 95%
of them men.

**The decrease is not capped** (owner, 2026-10-11): the term falls as far as the pool does, but not below −1, so the
engine's multiplier never goes negative. The +0.25 ceiling stays for now; the owner spoke only to the decrease. **This
changes phase 2**: aged rich countries no longer sit at a flat −25%, they get the pool's own shortfall. Today's rich
structure in the sketch is −0.25 (its pool happens to be at the old floor); an older one goes below it: −0.30 after 60
years of era 10's 0.9, and −0.43 by calendar age on the era 10 to era 11 ladder.

- **Decided (owner, 2026-10-11): both clocks.** The pool is men of calendar age 20 or more (legal adulthood) and
  biological age 39 or less (fitness). The war dead come from the same pool, whichever rule is chosen, so the dead are
  those who could be sent. Before life extension this is today's 20–39.
- **What it does** (sketch: everyone treated, 60 years from today's structure; the 1836 reference is 14.0% of people,
  28.6% of men):

| Case | Share of men in the pool: calendar 20–39 | Both clocks | Parent §7's term (from −1 up): calendar | Both clocks |
|---|---|---|---|---|
| Today's structure | 21.7% | 21.7% | −0.25 | −0.25 |
| Era 10 (ageing 0.9), 30 / 60 years | 21.0% / 20.4% | 23.2% / 22.5% | −0.28 / −0.30 | −0.20 / −0.23 |
| Era 10 for 20 years, then era 11 (0.75), 30 / 60 years | 19.5% / 16.6% | 23.7% / 21.1% | −0.33 / −0.43 | −0.18 / −0.28 |
| Immortality (3% pull), 30 / 60 years | 15.0% / 10.8% | 48.8% / 74.4% | −0.49 / −0.64 | +0.66 / +1.48 |

- **Under immortality nearly every adult man qualifies** under both clocks, and the term (+1.48 uncapped) sits at the
  +0.25 ceiling: the ceiling, not the pool, sets the late-game figure. By calendar alone the pool shrinks with the
  young cohorts and the term falls to −0.64, and the treated old are exempt however fit.
- **A player choice, later**: "service by age" against "service by fitness", with the Armed Forces favouring fitness
  (the owner thinks the group is usually too weak). Worth adding only if a play-test shows the ceiling binding often
  (§9, call 21).

## 3. Children: how many and when

### 3.1 Planned and unplanned births: the split the census already has

The census's fertility is wealth × natural × (1 − means × (1 − desired)) (`demographics_model.py:160`), which is the
sum of two parts:
- **Planned**: wealth × natural × means × desired, the families who choose their number;
- **Unplanned**: wealth × natural × (1 − means), the births the means don't reach.

**Decided (owner, 2026-10-11): planned births follow the calendar, unplanned births the body.**
- Planned births are timed by calendar age, the stage of life at which people form families; whether each happens
  depends on the body (§3.2). Lifetime planned births are at most the wanted number, however long people live.
- Unplanned births follow fecundity, over biological age. Under immortality they continue for as long as the body is
  fertile, as a trickle the means hold down.

Before life extension both read the same age and nothing changes. The split needs no new variable.

### 3.2 When: postponement and the biological window

- **Mean age at childbearing** is the planned schedule's one parameter. It rises with the postponement transition:
  education, women's work and the means (Kohler, Billari and Ortega 2002, *Population and Development Review*);
  Europe's rose from about 27 in the 1970s to about 31 today (*as summarised*). The schedule today
  (`ASFR_SHAPE_BY_GROUP`, `demographics_params.py:71`) has a mean of 30.1, a late-marrying natural schedule. Late
  Marriage's phase-3 "blended schedules" (#906's spec §2.5) are the same object: early in the game the Late Marriage
  share sets the mean, later postponement does. One parameter, two drivers, built once.
- **Fecundity by biological age** decides whether a planned birth happens: births postponed past what the body
  allows are lost. Proposal: 1 to 30, 0.9 at 35, 0.7 at 40, 0.35 at 45, 0 from 50 (after Leridon 2004, *Human
  Reproduction*, as summarised; assisted reproduction recovers part of the loss, which a biotech tech could carry).
- **Without counting the body twice.** Today's shape already falls with age, since it is a natural schedule (#906's
  spec §2.5). So the planned timing is the shape ÷ fecundity at calendar age, shifted by the mean age at
  childbearing, then × fecundity at biological age. With no shift and the two clocks equal, that is today's shape.
- So late postponement costs births, and life extension gives them back: a woman of 45 with the body of 35 has the
  child she postponed. That is the late game's answer to "when".
- **Phase 2 builds none of this** but keeps births computed as the two parts (§8.1).

### 3.3 How many: the completed-family bound (parent §13)

Under immortality, everyone treated, people after 50 years from today's structure, the body pulled 3% a year toward
35 (10% in brackets); "lifetime" is the children so far of women aged 100 at year 50:

| Fertility reads | People after 50 years | Lifetime children | Variables a state |
|---|---|---|---|
| Calendar age for all births | ×1.17 (×1.19) | 1.60 | none |
| **Planned by calendar, unplanned by biology**, means 0.9 | ×1.30 (×1.40) | 1.85 (1.99) | none |
| … means 0.95 (the cap) | ×1.23 (×1.30) | 1.73 (1.80) | none |
| Biological age, with §13's children-so-far bound | ×1.34 (×1.45) | 1.90 (2.06) | 30 (per band) to 150 |
| Biological age, no bound | ×1.86 (×2.29) | 2.95 (3.69) and rising | none |

Every run starts at 1.6 children per woman over calendar 15–49. The split's unplanned part is 3.0 children (Rich
today's wealth and natural terms) × (1 − the means): 0.3 at means 0.9, so 1.3 are planned. The §13 row stops planned
births at 1.6 and keeps an unplanned 3.5 × 0.1.

- **The split gives the bound §13 wanted for free.** Wanted families stay finite; the unplanned trickle
  goes on at about one child a century per woman at means 0.9 and half that at the cap, so §13's "slow trickle over
  centuries" is faster than §13 guessed, and the means matter more.
- **§13's children-so-far count** reaches almost the same numbers (planned births stop at the wanted size, unplanned
  go on), at 30–150 more variables. The calendar schedule does the counting.
- **Second families** (§13: "a higher wanted size brings a second family"): an optional planned tail at calendar
  50–100 for women whose bodies are fertile, switched on by a pronatalist measure under immortality. Not proposed for
  the first build.

### 3.4 The brake when deaths approach zero

- **In a rich, low-fertility state immortality turns decline into slow growth**: at 1.6 children per woman, ×0.75 in
  50 years with era 11 medicine alone becomes ×1.23–1.30 with the split (everyone treated). A swing of
  about a point a year, not an explosion: births per 1,000 fall as the adults pile up while deaths fall from about 8
  to 2.
- **A flat population needs low wanted fertility and near-perfect means, for good** (sketch, the pull at 3%, 60
  years): under the split, 1.0 children per woman still grows ×1.20 at means 0.9 and ×1.10 at the cap
  (0.95), because rejuvenated women of every calendar age add the unplanned trickle; 0.8 children at the cap gives
  ×1.06. With every birth timed by the calendar, 1.0 children holds it at ×1.02. Before immortality the line was about
  2.1. So Population Control's late role is to hold both the wanted size and the means, permanently, not for a
  generation.
- **In a high-fertility state growth was already fast**: at 3 children per woman the sketch grows ×2.18 in 50 years
  against ×1.91 without immortality.
- **The brakes are the means and the wanted size**, as §13 said: Free Contraception and Sex Education raise the means
  and so cut the trickle; Later, Longer, Fewer and Birth Limit cut the wanted size. Crowding and food security bring
  the engine's own brakes. Population Control matters most to the states that reach immortality young.
- **Owner's choice of feel** (§9, call 5): the split gives a slow, structural late game; reading biological age with
  §13's bound gives a stronger one; neither gives the parent §8.3's "every birth adds to the population" at low
  fertility.

### 3.5 Ectogenesis and Cloning Vats

- **Artificial wombs remove the body from planned births**: no maternal deaths and no fecundity loss for the share e of
  births they carry. Postponement then costs nothing, and births need not come from women of 15–49: the census counts
  that share's parents as the mean of women and men in the family-building ages, so a frontier or war-thinned
  population is not limited by its women.
- **e** = the state's ectogenesis capacity ÷ its births, at most 0.9 (proposal: 1,000 births a year per level of
  State Youth Centers on `pm_ectogenesis`).
- **The PMs' own birth lines stay on top** (+25% and +100% per level): births no family planned, raised by the state's
  Youth Centers. They act at the census's rate and the ring places them as newborns (the existing on-top path). They
  don't count toward any family's wanted size.

### 3.6 With Late Marriage, Birth Spacing and the means

- Late Marriage and Birth Spacing (#906) act outside the means as a product; both erode with contraception. By the late
  game they are near 0 almost everywhere, so they matter late only through the mean age at childbearing (§3.2).
- **The means' cap (0.95) becomes the immortal society's main brake** on the unplanned trickle. A late tech raising it
  (long-acting reversible contraception as the default) is a lever worth having; not proposed now.
- The child-survival term (`desired × (1 − 0.4 × (e0 − 30) ÷ 50)`) saturates at a life expectancy of 80, so longer lives
  don't push desired fertility further. The old-age-security motive (pensions lower fertility: Boldrin, De Nardi and
  Jones 2015) is a possible desired-fertility term for the pension age; not proposed.

## 4. Who gets life extension

### 4.1 What the engine can and can't do

- **The census is per state.** It has one ring a state; each band keeps its treated share and their deficit (§1.2),
  so the treated have their own age structure. It doesn't know which of a band's people are treated, only how many.
- **The engine's deaths are per pop**: bare curve × max(0, 1 + the state's terms + the pop's own). The only per-pop
  line that scales by wealth is `state_mortality_wealth_mult` ("Mortality per Wealth", `modifiers.log:1851`), which the
  census already drives through `te_dg_w` (`te_demog_rate_effects.txt:348`) on its own pair, Census: Deaths by Wealth
  (`te_demog_modifiers.txt:35-42`), for Private Health Insurance. Per pop type there are `state_<type>_mortality_mult`
  lines.
- **The census already knows who is rich**: people and income by 41 wealth bands per state (`te_dg_gn<k>`,
  `te_dg_gy<k>`), from the yearly walk.
- **So:** access is computed from the bands; the census's deaths count both parts; and the engine's per-pop deaths
  follow wealth through the existing pair. Who is treated is never stored on a pop. Per-strata effects other than
  deaths are state-wide modifiers or display.

### 4.2 Access: law × wealth × time

For wealth band k, access a_k is the larger of two routes; eligibility E (§1.2) drifts toward their people-weighted
mean.

- **Public route**: the health system pays. Its reach is the census's health-care access (base 0.4 plus the health
  law per level, drifting, from the Causes of Death plan) times the law's cover for longevity care.
- **Market route**: people buy it. A band is within reach when its wealth is above a threshold W that falls with time
  since the first carrier: from wealth 80 (the top of the upper strata) by 1 a year, faster with the medical-diffusion
  type of the Causes of Death plan. Within ±10 of W, access ramps from 0 to 1. Anchors: new medicine starts at the top
  and falls in price; antiretrovirals went from about $10,000 a patient-year in 2000 to under $100 a decade later
  (*as summarised*); today's gene therapies cost $2–3.5 million a dose.

| Law | Effect on access (proposal) |
|---|---|
| Public Health Insurance | public cover 1: everyone the health system reaches |
| Private Health Insurance | public cover 0; the market threshold falls twice as fast (insurers pool the price) |
| Charitable Health System | public cover 0.25 |
| No Health System | market only |
| Human Purity | none: banned (the Devout's law) |
| Unrestricted Augmentation | the market threshold starts at 60, not 80 |
| Regulated Augmentation Market | the market threshold falls 1.5 times as fast |
| Medical Augmentation Only | no change (longevity care is medicine) |
| Mandatory Augmentation | public cover 1, and access at least 0.9 |

**Built as law modifiers (2026-10-17).** Each row's effect is a census-only type on the law's own `modifier` block (`state_longevity_care_cover_add`, `_floor_add`, `_market_reach_add`, `country_longevity_care_banned_bool`, `country_longevity_care_price_fall_mult`), so the law's tooltip says what it does and the census and its Python twin read the lines rather than `has_law`. Unrestricted Augmentation's start at 60 is the threshold 20 lower throughout. The two faster falls add as modifiers do: Private Health Insurance +100% and the Regulated Augmentation Market +50%, ×2.5 together where the factors multiplied to ×3.

The augmentation laws already sort the strata this way (Unrestricted gives the upper strata SoL +5 and the lower −1),
so access needs no new law group. Alternative considered: a new law group for longevity care; rejected, since the
health and augmentation laws already say who gets medicine and enhancements.

### 4.3 The longevity gap, and who actually dies

- **The gap** is the difference in the chance of living to 100 between the treated and the untreated (two life
  tables, a step each). Points of a bounded figure, not years: under immortality the years are in the hundreds. The
  sketch's era 11 gap is 67% against 35% (32 points); under immortality 81% against 35%.
- **Today's gap, for scale:** the richest 1% of American men live 14.6 years longer than the poorest 1%, women 10.1
  (Chetty et al. 2016, *JAMA*); the census's Private Health Insurance line is the game's version.
- **The ring and the gap agree.** The ring's treated and untreated parts die at the two life tables' rates (§1.3), so
  the gap the panel shows is the ring's.
- **Who dies in the engine.** The census fits a wealth slope to its wealth bands each step and puts it on the existing
  Census: Deaths by Wealth pair. Each wealth band's death multiplier is 1 − (its treated share) × (1 − ρ), where ρ is
  the ring's treated deaths per head ÷ its untreated deaths per head; the wealth bands' treated shares are their
  access, scaled so their mean is the ring's treated share (which selection has raised). The slope is that multiplier
  against wealth, people-weighted. Rich pops then really die less, grow relative to the poor and shift the strata.
- **The slope is the census's own, so M nets it**, as it nets the absorbed per-pop terms: the walk sums each pop's bare
  curve × its slope term, floored where the engine floors a pop (max(0, 1 + …): no pop's deaths go below zero), and M
  takes that sum out. Under immortality ρ is about a fifth at 70 and a twentieth by 85, and a straight slope would take
  the richest pops below zero; the top wealth band is held at ρ, and what the floor removes goes back into M, so the
  state's total stays the model's.
- **This overturns option (b) in effect** (owner, 2026-10-11: Private Health Insurance's wealth line at least −0.005 a
  wealth level, `demographics_params.py:246`, so a wealth-99 pop dies at no less than half the census's rate). The
  floor stays on that line; the longevity slope adds to it on the same pair, so once longevity care exists a rich pop
  dies at a fraction of the census's rate (§9, call 14).
- **Alternative**: per pop type lines (Aristocrats and Capitalists treated first). Coarser, and wrong under Public
  Health Insurance, where access doesn't follow class.

### 4.4 Political consequences (proposal, small)

- **Trade Unions and Rural Folk approval** (`interest_group_ig_trade_unions_approval_add`,
  `interest_group_ig_rural_folk_approval_add`, country) fall by up to 3 with the national gap × the lower strata's
  untreated share; one country modifier, refreshed yearly.
- **Labor movement support** rises in states where the gap is large (`state_pop_support_movement_labor_add`, state,
  from the state pulse).
- **Wealth Concentration**: continuity of title (`inheritance_events.txt:417`) already pins the target under
  immortality. Under era 11 the rich die less often and estates pass less often: a target term of +5 × the upper
  strata's treated share × (1 − r) is an option, not proposed for the first build.
- No `is_ai`; the AI picks its health and augmentation laws by the same weights.

## 5. Who pays for the old

Like every census effect, the workforce term (§2.1) and both bills below apply under Full only. Display only shows
them as figures, and the pension setting is hidden outside Full, as the Causes of Death plan hides its decree.

### 5.1 The pension: money

- **Who is paid**: people at or above the pension age, under Old Age Pension (§2.2).
- **How much**: a weekly expense of GDP ÷ 52 × the pensioners' share × B, where B = 0.08 per level of Social Security
  (0.4 of GDP per head per pensioner at level 5). The mod's pattern: a static modifier with `country_expenses_add = 1`
  and a GDP-scaled multiplier (`scripting_best_practices.md`, "Expense Scaling with GDP"; `modifiers.log:595`).
- **Anchor**: OECD public pensions cost about 8% of GDP with about 18% of people over 65 (OECD, *Pensions at a Glance
  2023*, as summarised): about 0.4 of GDP per head per pensioner.
- **B waits for a fit.** The OECD anchor is a share of GDP, and the game's government revenue as a share of GDP is
  unmeasured (the same open check as `monetary_policy_design.md` §12.2). The harness fits B against revenue in a
  late-game save before the numbers are tuned.
- **Sizes (sketch, B = 0.4)**: rich today at 65, 31% pensioners → 12% of GDP. Under immortality (§2.3's table), 60
  years on: 65 → 27% and still rising; Linked to Common → 21% (14% after 30 years); Linked to Average → about 6–7%,
  the pensions of those already retired when immortality came.
- **Stacks on vanilla's welfare, by recipient** (§9, call 17). Old Age Pension's `state_welfare_payments_add` (+0.1 a
  level) goes to workers paid below a share of the normal wage, not to the old (parent §14 Q6). Its +20% dependents'
  income a level has no payer: this bill is that payer. The owner confirmed it (2026-10-11): vanilla's +20% dependents'
  income has no treasury cost (also parent §14 Q6, from the game files). Under UBI and Post-Scarcity (welfare payments
  0.8 and 4.8 a level, `extra_laws.txt:313`, `:370`) everyone is paid already, so there is no pension bill (§2.2).
- **Replaces** the parent §7's bureaucracy-only pension bill, as #894 ruled.

### 5.2 Health care: bureaucracy

`country_institution_cost_institution_health_system_mult` (`modifiers.log:5353`) gets three terms, one country
modifier, refreshed yearly:

| Term | Proposal | Late-game behaviour |
|---|---|---|
| **Need**: the people-weighted health need ÷ 1836's − 1, × 0.5 | weights by biological age: 0–4 1.0, 5–14 0.5, 15–44 0.8, 45–64 1.4, 65–74 2.4, 75–84 3.4, 85+ 4.5 (after American health spending per person by age, CMS, 2020, rounded; *as summarised*) | rich today +0.39; era 11 medicine alone +0.59; ageing at 0.5 +0.37; immortality −0.09 |
| **Medical technology** | +0.05 for each chronic-treatment tech (`modern_pharmaceuticals`, `telemedicine`, `personalized_medicine`) | +0.15 at era 11: the owner's "moderately" |
| **Longevity care paid by the system** | +0.5 × the share of people on the public route | up to +0.5 under Public Health Insurance or Mandatory Augmentation |

The need term reads biological age, so it doesn't count calendar years: the 300-year-old with the body of 35 costs
what a 35-year-old does. That is the late game's health bill: geriatric care gives way to the treatment that keeps
everyone young.

### 5.3 What keeps them bounded

- **Health**: the weights stop at 85+, the need term is capped at +1.0, and slowing the clock lowers need. The worst
  case is era 11 medicine without slowing, not immortality.
- **Pensions**: bounded by people (at most every adult over the pension age, about 35% of GDP at B = 0.4). A fixed age
  under immortality is the expensive choice by design. Linked to Average Longevity is the cheap way out, at the price
  of the untreated's pensions and a legacy of 6–7% of GDP for those already retired; Linked to Common Longevity keeps
  the untreated's pensions at a bill that reaches Standard's within two generations. The Pension Without End (§2.2)
  offers the choice.
- **AI**: picks the setting by the bill's share of its GDP and its treasury (the parent §11.2's rule), the same
  weights for every country.

## 6. The panel

### 6.1 What replaces life expectancy

| Candidate | Under immortality | Verdict |
|---|---|---|
| Life expectancy at birth | 559 years, or 129 cut at 150 | keep while under 100; then "100+" |
| Median age at death | 594 for women, 203 for men | no: it splits by sex on the external rates, and reads as nonsense |
| **Living to 100** | 81% | **yes**: bounded, readable in every era from 1836's 0% to now and on |
| **Old age from** (the age with 15 years left; Sanderson and Scherbov 2005, *Nature*, and 2010, *Science*) | none | **yes**: says what "old" means now, and drives the linked pension positions |
| Deaths per 1,000 | 2.2 | already shown (realized); in the late game it is the honest figure |
| Healthy lifespan (years to biological 65) | unbounded | no: undefined under immortality |
| **Mean biological age** | 29 against a calendar mean in the hundreds | **yes**, from the first ageing carrier (era 10) |

### 6.2 The rows

All "Label: value" with the breakdown on hover (style guide rules 1, 3, 5). Country figures are people-weighted over
the census states.

| Row | Section | Shown | Value | Hover |
|---|---|---|---|---|
| Life expectancy | Overview; state figures | always | `77`, then `100+` once the census's figure passes 100 | at birth and 65, women and men, the five causes (as built) |
| Old age from | Overview; state figures | phase 2 | `75`, or `none` | 15 years left; women and men; the untreated's figure beside the state's; the linked pension positions sit five years below the one they follow |
| Living to 100 | Overview; state figures | from era 10's step, or once 1% | `35%` | treated and untreated; women and men |
| Biological age | Overview; state figures | from era 10's step | `38 (calendar 61)` | mean ages; the ageing rate; the pull; the treated share |
| Workforce | Work and Retirement (new, open) | phase 2 | `62% × 71% = 44%` | working-age share by its bounds; at work by sex and class mix; workers past the pension age |
| Pension age | Work and Retirement | Old Age Pension | `84 (Linked to Common)` | the setting's five buttons sit beside it (rule 6), each with its trade-off, interest-group reactions and minimum term on hover, greyed with the reason while the term runs or outside Full; the threshold the position follows |
| Pensioners | Work and Retirement | Old Age Pension | `18%` | |
| Pension bill | Work and Retirement | Old Age Pension | `£1.2M a week (6% of GDP)` | pensioners × B |
| Health need | Work and Retirement | phase 2 | `×1.8 of 1836` | by age band; medical technology; longevity care |
| Longevity care | Longevity (shown from era 10's step, rule 7) | era 10's step | `42% of people` | by strata; the market threshold ("within reach from wealth 45"); the laws |
| Longevity gap | Longevity | era 10's step | `32 points` | living to 100, treated and untreated; the approval and movement effects it drives |
| Mean age at childbirth | Overview, children per woman's hover | phase 3 | `31` | planned and unplanned; births lost to postponement |

- **Children per woman** stays the conventional figure over calendar 15–49; its hover adds births to women over 50
  when there are any.
- **The parent §10 put the pension setting in Family Policy.** Retirement isn't family policy; it moves to Work and
  Retirement.
- **The pyramid's toggle** (decided): in biological mode each cohort's treated part sits at its biological band and
  the untreated part at its calendar band, so a half-treated society shows two shapes over each other. The calendar
  pyramid grows a column, the parent's "late game's striking image"; the top bar reads 150+.
- **State subtab**: the same rows for the state; the Causes of Death section's chronic row gains "Biological age −N
  years" on hover.
- **History** adds Living to 100 from era 10's step (optional).

## 7. Cost

| Item | Variables a state | When | Save (887 states, 60–85 bytes each) |
|---|---|---|---|
| Phase 2 figures: working-age share, share at work, pensioners, health need, old-age threshold, the workforce term | 6 | always | about 0.4 MB |
| Phase 3: E, r, c and the pull; a treated share and a deficit per band (up to 50) and the pool's two; Living to 100 treated and untreated; mean biological age; access by strata (3); mean age at childbirth | up to 62 | from era 10's step, states with someone treated | about 3.9 MB |
| … with one deficit per band instead | up to 37 | | about 2.3 MB |
| … with a share and a deficit per slot instead | up to 262 | | about 16 MB |
| §13's children-so-far (not chosen) | 30–150 more | | 2–9 MB |

Against about 345 a state today (363 with the Causes of Death plan: +18 under Full). The country adds a handful (the pension age and
setting, the bill's multipliers, the gap).

**Time.** Phase 2's figures are sums the sweep already visits. Phase 3 doubles the rate work for the treated slots (a
lookup and a second rate a slot) and the life tables (treated and untreated): about 1 ms → 2 ms a state, on its own
day; the per-band selection update adds 25 divisions. The pop walk gains nothing: access reads the stored wealth
bands. Owner check 5 (the benchmark in a late-game save) is the gate; per-band storage keeps the risk small.

## 8. Phasing

### 8.1 Decide now: what phase 2 builds so it doesn't bake in 1836

1. **Two indexes in the sweep.** Phase 2's new per-age sums (workers, pensioners, health need, the conscription pool
   and the war dead's window) read a biological index that is the calendar index until phase 3: one local per slot,
   no variable.
2. **The pension age is a country variable**, set by the setting; nothing compares with a literal 65. The five
   positions (§2.2) can ship with phase 2: the linked ones need only the old-age thresholds, which the life table
   already allows (before life extension the two are the same).
3. **Participation is a table over ages** in `demographics_params` (working-age start by law, capacity by biological
   group, the after-pension share), not a 15–64 band.
4. **Health need is a weight table by biological group**, not a 65+ share.
5. **Births are computed as planned plus unplanned**, each with its own schedule (the same one in phase 2).
6. **The old-age threshold** is computed and stored at each step (a reverse pass over the life table's 31 groups).
7. **Names reserved**: `te_dg_d<j>` (deficits), `te_dg_s<j>` (treated shares), `te_dg_elig`, `te_dg_cover`,
   `te_dg_age_rate`, `state_ageing_rate_add`, `state_rejuvenation_add`.
8. **The workforce target is a total** (§2.1): phase 2's term nets the pops' base ratios and the lines left on top,
   and the women's-work and retirement lines move to script-only types the participation model reads. No cap.
9. **Conscription's term falls as far as the pool does**, to −1 (§2.5): parent §7's −0.25 floor goes.

Items 1–7 change no number phase 2 would otherwise produce. Item 8 decides how phase 2's own workforce term counts
the lines already there; item 9 changes parent §7's conscription figure for aged countries.

### 8.2 Phase 3

The ageing rate and its carriers; who is treated (a share and a deficit per band, eligibility and cover);
Biological Immortality's pull; access and the wealth slope; the longevity
gap and its politics; the two fertility schedules, postponement and fecundity; ectogenesis's share; the late display
rows; the late-era lines' move into the census (§8.4); the late check of adult external and work rates (§1.4).

### 8.3 Dependencies on work in flight

- **Causes of Death (#905)**: health-care access drifts; the public route of §4.2 reads the drifted access, and its
  medical-diffusion rate sets how fast eligibility drifts (§1.2) and speeds the market threshold. Its section gets the
  biological-age line (§6.2). No conflict.
- **Late Marriage and Birth Spacing (#906)**: their phase-3 blended schedules and §3.2's mean age at childbearing are
  one parameter; build it once, in phase 3.
- **#894's workforce from participation**: §2.1 is that model with capacity added as its upper bound when there is no
  pension; write it into the parent §7 with this design's clocks.
- **The pension money cost (parent §13)**: §5.1 is the proposal it asked for.

### 8.4 The late-era lines on top

| Line | Today (on top) | Under Full (proposal) | Outside Full |
|---|---|---|---|
| `biological_immortality` −0.20 deaths | on top | census: r = 0, the pull | flat line stays |
| `mental_health_awareness` −0.05 deaths | on top | census: external −10% (a `state_external_mortality_mult` line) | flat line stays |
| `mind_backups` −0.05 deaths | on top | census: external and work −50% | flat line stays |
| `pm_ectogenesis`, `pm_cloning_vats` births | engine lines in the state read, so at the census's rate | stay so (§3.5); the census adds e | as now |

Each moves from `ENGINE_LINES_ON_TOP` to the absorbed family as parent §8.4's lines did, so M cancels it under Full
only.

## 9. Owner calls (all decided, 2026-10-11)

The owner approved every call as recommended. Call 15 waits for a play-test and call 16's B for a fit. Calls 5,
13 and 14 depend on calls 1 and 12. Each alternative is kept as the one considered.

1. **Two clocks**: deaths, capacity, health need and unplanned births read biological age; pension eligibility and
   schooling read calendar age; planned births read both, calendar for their timing and biology for whether the body
   allows them; conscription is call 21 (§0). This amends the parent §1's "every age-specific rate reads biological
   age". *Decided (owner, 2026-10-11).* Alternative considered: the parent's single clock with §13's bound.
2. **Phase 2 builds the interfaces in §8.1** (two indexes, a pension-age variable, participation and need tables,
   planned and unplanned births, the workforce target as a total), changing no number it would otherwise produce.
   *Decided (owner, 2026-10-11).*
3. **The ageing ladder: 0.9 at era 10, 0.75 at era 11, 0 at era 12.** *Decided (owner, 2026-10-11)* for era 10's step
   (0.9, the owner's value); carried by `mrna_therapeutics` −0.10, then `personalized_medicine` −0.10 and
   `genetic_engineering` −0.05. Treated life expectancy about 82 at 0.9 and 103 at 0.75. Era 11's 0.75 is decided too;
   the parent's 0.5 (about 130) was the alternative. *Amended (owner, 2026-10-16):* era 11 reaches 0.70, with
   `synthetic_biology` −0.05 taken from `biological_immortality` (now −0.70), so some of the slowing arrives an era
   earlier; era 12 is still 0. The census's treated life expectancy at 0.70 is about 110 (105 at 0.75).
4. **Immortality's pull toward 35: 3% a year** (deaths per 1,000 from 8 to about 3.6 in ten years). *Decided (owner,
   2026-10-11).* Alternative considered: 10% (2.4 in ten years).
5. **Fertility under immortality: planned by calendar, unplanned by biology**, no new variables; growth ×1.23–1.30 in 50
   years at 1.6 children with everyone treated (§3.3). *Decided (owner, 2026-10-11).* Alternatives considered: §13's
   children-so-far count (×1.34, 30–150 more variables), or biological age with no bound (×1.86 and rising).
6. **The pension setting: five positions**, Early 60, Standard 65, Raised 70, Linked to Average Longevity and Linked to
   Common Longevity (both linked ones five years below the old-age threshold they follow, at most a year a year, 70
   today), each with a five-year minimum term. They are buttons in the Demographics tab's Work and Retirement section,
   shown only under Old Age Pension and greyed with the reason while the term runs or outside Full; the AI picks on its
   yearly pulse by the bill's share of GDP, the treasury and the longevity gap, the same for every country. *Decided
   (owner, 2026-10-11)*, with the linked floor of 65 (it brings back a fixed age on purpose, so linking only raises the
   age; without it, about 56–60 before 1950) and the interest-group reactions (Early: Trade Unions +2, Industrialists
   −1; Raised: Trade Unions −2, Rural Folk −1, Industrialists +1; Average: Trade Unions and Rural Folk −1,
   Industrialists +1; Common: Trade Unions and Rural Folk +1, Industrialists −1).
7. **Both linked variants are offered** (owner, 2026-10-11). Linked to Average Longevity follows the state's blended
   table: the cheapest under immortality (16% pensioners and about 6% of GDP after 60 years, everyone treated), but the
   untreated, who still age, may never reach it, the real regressive effect of indexing. Linked to Common Longevity
   follows the untreated's table: fairer, but the treated draw a pension from about 84 for ever (54% pensioners and
   about 21% of GDP after 60 years). *Decided (owner, 2026-10-11).*
8. **Who is treated: a treated share and a deficit per five-year birth band** (up to 50 variables a treated state, about
   3.4 MB in a full late save). It tracks the truth within 0.1 deaths per 1,000 in every case of §1.3's table, and the
   ring then has the gap §4.3 shows. *Decided (owner, 2026-10-11).* Alternatives considered: one deficit per band over
   the whole cohort (25 variables; right under era 11, but under immortality with half the state treated it gives 3.3
   deaths per 1,000 against 7.6, and the gap becomes display only); a share and a deficit per slot (up to 250, exact).
9. **Losing care: bodies keep their age.** The formerly treated age at 1 from where they are; eligibility drifts at the
   Causes of Death plan's medical-diffusion rate both ways; emigrants leave with their band's mix, and immigrants,
   Internal Resettlement's included, join at the destination's (§1.2). *Decided (owner, 2026-10-11).* Alternative
   considered: the first draft's snap to calendar age (a ban after 50 years of immortality takes deaths from 2.2 to 42.6
   per 1,000 in a year).
10. **The workforce ratio is uncapped.** *Decided (owner, 2026-10-11).* The harness and an observer run watch the
    engine-scale figures: about 0.62 under Linked to Average, 0.36 under Linked to Common and 0.73 with no pension under
    immortality, against 0.25 in 1836 and 0.42 today. More labour per pop means unemployment and lower wages where jobs
    don't grow with it, output where they do. A cap comes only if those runs show a problem.
11. **The workforce target is a total**: the census's term nets the pops' base ratios and the lines left on top; the
    women's-work lines (the women's-rights laws, the Pill, second-wave feminism, personal appliances, two family-policy
    laws) and the retirement lines (Old Age Pension, UBI, Post-Scarcity, Pro-Natalist) move to script-only types the
    participation model reads, cancelled under Full only (§2.1). This amends the parent's rule 3. *Decided (owner,
    2026-10-11).* Alternative considered: add the census's term on top of every line, and women's work counts twice.
12. **Access by law × wealth band × a falling market threshold**, through the existing health and augmentation laws
    (§4.2's table). *Decided (owner, 2026-10-11).* Alternatives considered: a new law group; access by health-care
    access alone (no rich-first).
13. **Health bureaucracy: need by biological age (× 0.5, capped +1.0), +0.05 per chronic-treatment tech, +0.5 × the
    publicly covered longevity care.** *Decided (owner, 2026-10-11).*
14. **Rich pops really die less**: the census fits a wealth slope from its wealth bands onto the existing Census: Deaths
    by Wealth pair, M nets it with each pop floored at zero deaths, and the top band is held at the treated's rate
    (§4.3). This overturns option (b)'s effect in the late game: option (b)'s −0.005-a-level floor stays on Private
    Health Insurance's line, but a rich pop with longevity care dies at a fraction of the census's rate, not at half.
    *Decided (owner, 2026-10-11).* Alternative considered: the gap as display and politics only, every pop dying at the
    state's rate.
15. **The gap's politics**: Trade Unions and Rural Folk approval down to −3, Labor movement support up, both scaled by
    the gap and the lower strata's untreated share. *Decided (owner, 2026-10-11): play-test later*: build the gap and
    its display first, and size the politics when a game shows one. *On at these sizes since 2026-10-16 (owner): the
    play-test checks them instead.*
16. **Pension money cost: GDP ÷ 52 × pensioners' share × B**, B = 0.08 per Social Security level as a starting value.
    *Decided (owner, 2026-10-11): B is fit later*, against the game's revenue in a late-game save before tuning.
17. **The pension bill stacks on vanilla's welfare by recipient**: Old Age Pension's welfare payments go to low-paid
    workers and stay; this bill pays for the old, whose +20% dependents' income vanilla gives without a payer; UBI and
    Post-Scarcity pay everyone already and have no pension bill (§5.1). The "no payer" premise is the owner's
    confirmation (2026-10-11). *Decided (owner, 2026-10-11).* Alternatives considered: replace Old Age Pension's welfare
    payments with the bill; or charge the bill under UBI and Post-Scarcity too.
18. **The panel**: Life expectancy shows `100+` past 100; add Old age from (phase 2), Living to 100 and Biological age
    (from era 10's step); a Work and Retirement section that takes the pension setting from Family Policy; a Longevity
    subsection from era 10's step. *Decided (owner, 2026-10-11).*
19. **The late-era lines** move into the census under Full (§8.4): immortality as the ageing rate, Mental Health
    Awareness as external −10%, Mind Backups as external and work −50%; ectogenesis's births stay on top. *Decided
    (owner, 2026-10-11).*
20. **The adult external and work schedules get a 2000–2020 band in the harness** before phase 3, since under
    immortality they are the whole death rate (men's median age at death 203 against women's 594 in the sketch).
    *Decided (owner, 2026-10-11).*
21. **Conscription.** *Decided (owner, 2026-10-11)*: the decrease is not capped; the term falls as far as the pool does,
    down to −1, and the +0.25 ceiling stays for now. This changes phase 2 (§2.5): aged countries get the pool's own
    shortfall instead of a flat −25% (today's rich structure −0.25; −0.43 by calendar age after the era 10 to 11
    ladder). Also decided: the pool reads both clocks, men of calendar age 20 or more and biological age 39 or less, and
    the war dead come from the same pool, whichever rule is chosen. Under immortality 74% of men qualify after 60 years,
    and the term (+1.48) sits at the +0.25 ceiling. Alternatives considered: calendar only (the treated old are exempt
    and the pool shrinks to 11% of men after 60 years of immortality, a term of −0.64); biological only (no legal floor:
    rejected); a player choice, "service by age" or "service by fitness", with the Armed Forces favouring fitness, added
    only if a play-test shows the ceiling binding often.
