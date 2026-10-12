# Demographics in the late game: old age, work, children and who lives longest — design (scoping draft)

> **Status: scoping draft, 2026-10-11, first round.** It answers the owner's request of 2026-10-11: scope the late
> game's demography as one model before phase 2's workforce, pension and health work bakes in early-game assumptions.
> Parent spec: `2026-10-08-demographics-design.md` (cited as "parent §n"); this draft amends its §1 ("Ages past 95
> and the late eras"), §7, §8.2, §8.3, §10 and §13 ("Fertility without ageing") where it says so. It builds on #894's
> rulings (workforce from participation; who pays for the old) and on two plans in flight: Causes of Death (draft PR
> #905, branch `feat/demog-causes-of-death`) and Late Marriage and Birth Spacing (draft PR #906). No code here. Every
> number is a starting proposal for the harness. Figures marked *sketch* come from a throwaway Python run of the
> census's own model (`demographics_model.py`, the harness's Rich-today inputs) extended with a biological clock; they
> are the model's arithmetic, not history. Anything past today is speculation, marked as such.

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
few and seventy years to play out, and nobody reaches the pool at 150 except in the most extreme games.

**The risk the owner named.** Phase 2 is about to write the workforce effect (ages 15–64, an over-65 share), the
pension bill (a 65+ count) and the health bill (a 65+ share). Each would be wrong by the late game: 65 stops meaning
old, the 15–64 band stops meaning working, and a 65+ count stops measuring need. This draft fixes the interfaces now
and leaves the late mechanics for phase 3.

### What the census's own arithmetic says (sketch)

Life tables from the harness's Rich-today inputs (Public Health Insurance at level 8, medicine to era 10, SoL 40),
both sexes' mean. "Ageing 0.75" means the treated age three-quarters of a year each year from 25.

| Case | Life expectancy | At 65 | Living to 100 | Old age from (15 years left), women / men |
|---|---|---|---|---|
| Britain 1836 | 39.8 | 12.5 | about 0 | 63 / 60 |
| Rich today | 77.5 | 21.7 | 9% | 77 / 73 |
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
"workforce" is the share of all people at work under modern women's participation and §2.1's capacity table, with a
pension at 65 or none):

| Case | People at 30 / 60 years | Deaths per 1,000 at 30 | Calendar 65+ at 60 | Mean biological age | Health need (1836 = 0.97) | Workforce at 60: pension 65 / none |
|---|---|---|---|---|---|---|
| No change | 0.75 / 0.56 | 17.9 | 31% | 48 | 1.71 | 0.45 / 0.55 |
| Era 11 medicine, no slowing | 0.88 / 0.68 | 14.6 | 42% | 56 | 2.11 | 0.38 / 0.49 |
| Ageing 0.75 | 0.93 / 0.79 | 11.1 | 50% | 54 | 1.94 | 0.35 / 0.55 |
| Ageing 0.5 | 0.97 / 0.90 | 8.6 | 56% | 50 | 1.69 | 0.33 / 0.61 |
| Immortality, pulled 10% a year toward 35 | 1.13 / 1.22 | 2.2 | 67% | 29 | 0.79 | 0.29 / 0.77 |

Three things fall out, and the rest of the draft is built on them:
1. **Medicine that treats without slowing ageing makes a society older and sicker** (health need 1.73 → 2.11). Only
   slowing the clock relieves it. That is the owner's "medical tech moderately raises health cost", with a reason and
   an end (§5.2).
2. **A pension at calendar 65 under immortality makes two-thirds of the people pensioners**, and the workforce falls
   to 0.29 against 0.77 with no retirement. The pension age must be able to follow longevity (§2.2).
3. **Whether immortality is a population shock depends on which clock fertility reads** (§3.3): ×1.19 in 50 years when
   families are timed by calendar age, ×2.29 and rising when fertility reads biological age with no bound.

## Rulings this draft keeps

| Ruling | Source |
|---|---|
| Nothing changes outside Full; Display only shows what Full would do | owner, 2026-10-10 |
| General mechanisms, no country- or culture-specific mechanics; asymmetric outcomes through shared mechanics, never `is_ai` | owner; memory |
| Workforce from participation; working-age share × share at work = workforce on the panel | #894 |
| Pensions cost money, health care costs bureaucracy; medical technology moderately raises the health cost; no hard-coded 65 | #894 |
| Growth matters more than exact children per woman; drift over jumps | #894 |
| Pension age as a setting under Old Age Pension, not amendments. The parent's three positions stand; a fourth, Linked to Longevity, is proposed (§2.2, call 6) | parent Decisions |
| Calendar/biological toggle on the pyramid from era 11; ring to about 150 from 1836 | parent Decisions |
| Measures are GUI buttons, national for now | parent Decisions |
| One-year cohorts at about 26 MB of an 1836 plain-text save | #894 |

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
| Planned births (the wanted family) | calendar | families are formed at a stage of life (§3.1) |
| Pension eligibility | calendar | the law reads a birth date |
| Schooling and child labour (the working ages' lower bound) | calendar | law |
| Conscription's ages, war dead (18–40), youth bulge (20–29), migrant classes | calendar | law and life stage |
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
  (Harrison et al. 2009, *Nature*); no intervention has slowed human ageing. Everything from era 11 here is
  speculation, placed so that era 11 is a step and era 12 the leap.

### 1.2 Biological age: who is treated, and how fast they age

**Two state figures and a deficit per cohort.**
- **The treated share A** (0–1): the share of the state's adults with life-extension care. Access sets it (§4).
- **The ageing rate r** of the treated: biological years per calendar year. 1 until the first carrier; read from a new
  script-only state type, `state_ageing_rate_add` (negative), as the census reads its other types.
- **The deficit d** per cohort: calendar age − biological age of its treated part. The untreated part is at its
  calendar age. Children are not slowed: the deficit grows only past maturity (25).

Each year, for each adult cohort: d += (1 − r); and when A rises, the newly treated arrive with no deficit, so
d × A_old ÷ A_new before the year's growth (when A falls, the leavers take the mean, and d stays). The pool keeps one
deficit like its mean age.

**Carriers (proposal; speculation):**

| Carrier | Era | `state_ageing_rate_add` | Why |
|---|---|---|---|
| `personalized_medicine` | 11 | −0.15 | geroprotective drugs (the rapamycin class) |
| `genetic_engineering` | 11 | −0.10 | gene therapies against the hallmarks of ageing |
| `biological_immortality` | 12 | −0.75 (r = 0) and `state_rejuvenation_add` +0.03 | ageing stops; the body winds back |

Era 11 together gives r = 0.75: a treated person's steady-state life expectancy is about 103, near the optimistic end
of extrapolations (best-practice life expectancy has risen about three months a year since 1840, Oeppen and Vaupel
2002, *Science*; against that, Olshansky et al. 2024, *Nature Aging*, argue radical extension this century is
implausible). The parent proposed about half a year a year at era 11 (r = 0.5); that gives 130 and an old-age
threshold past the ring (§9, call 3).

### 1.3 How the ring carries it

The sweep reads each slot's rates at its biological index. For the treated part that is a lookup, not the running
pointer: precompute each group's rates once per step (31 groups, two sexes, as locals), then take a slot's treated
rates by a generated five-comparison tree on its biological age. A cohort's deaths are A × the treated rate + (1 − A)
× the calendar rate. The sum of rates, not a mean age, because deaths are convex in age: on women's chronic base, half
a cohort at 60 and half at 90 die at (1,700 + 22,000) ÷ 2 per 100,000, not at 75's 6,200.

**Three ways to store the deficit** (each from era 11 only, in states with A > 0):

| Option | Variables a state | Exact? | Notes |
|---|---|---|---|
| **Per slot** (the parent's) | up to 125 (adult slots) + pool | yes, up to the mean over the treated | simplest code; about 8 MB more in a full late save |
| **Per five-year birth band** (recommended) | up to 25 + pool | within a year, except a band crossing maturity or under a strong pull (the band's five cohorts sit within ±2 years of each other) | band = birth year ÷ 5 mod 30, which nests in the ring's 150; the display bands are five years anyway; about 1.6 MB |
| **Parametric** | 2: the years not aged since onset, D, and r | exact only while r has been constant since onset: biological = calendar − min(D, (1 − r)(calendar − 25)) | breaks at era 12, under rejuvenation and when A changes, which are the late game's events |

Migrants join their destination's cohort and take its deficit and access: care follows where people live. A state
seeded after era 11 (a new or split state) seeds its deficits at the steady state of its current r: (1 − r) ×
(calendar − 25).

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

### 1.5 Old age from: the old-age threshold

- **"Old" as a number**: the age at which a state's people have 15 years of life left on average, Sanderson and
  Scherbov's prospective old-age threshold (2005, *Nature*; 2010, *Science*).
- **Its values** (sketch, women / men): 63 / 60 in 1836, 66 / 63 in 1950, 77 / 73 today, 92 / 86 with era 11
  medicine, 117 / 110 with ageing at 0.75. Under immortality there is none: no age has only 15 years left.
- **How**: from the census's own life table, a reverse pass over its 31 groups at each step; the treated and untreated
  tables weighted by A; women and men averaged. A period figure, like life expectancy.
- **What reads it**: the panel's Old age from row; Linked to Longevity (§2.2); the after-pension share under UBI and
  Post-Scarcity (§2.2); events that mean "the old". Deaths, capacity and health need don't: they read biological age
  directly.

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
(`modifiers.log:2007`), scaled so a typical 1836 state lands on vanilla's 0.25 (#894). Immortality with no retirement
gives about 1.7 times today's fraction (0.77 against 0.45 in the sketch), about 0.7 on the engine's scale. Vanilla
never goes past 0.5 (slaves), so a cap is an owner call (§9, call 7; proposal 0.6).

### 2.2 The pension age

**The pension age is one number per country**, stored as a variable (a revolution's winner keeps it; CLAUDE.md, "the
winner continues the nation"), read by the workforce (§2.1), the pension bill (§5.1) and the panel. The setting under
Old Age Pension chooses how it is set:

| Position | Pension age | Who wants it |
|---|---|---|
| **Early Retirement** | 60 | Trade Unions, the old; frees jobs for the young (parent §8.2) |
| **Standard** | 65 | the default |
| **Raised Pension Age** | 70 | the treasury, Industrialists |
| **Linked to Longevity** (new) | five years below the old-age threshold (§1.5), never below 65, moving at most a year a year | the treasury; Trade Unions object less than to Raised, since it rises only as lives lengthen |

- **Why a fourth position and not indexed defaults.** Indexing every position would remove the 20th century's fiscal
  squeeze: a fixed 65 that grows more generous as lives lengthen *is* the history (Germany's 70 in 1889, 65 from 1916;
  65 held for most of a century while life at 65 grew by about eight years). Linking is the early-21st-century reform:
  Denmark linked its pension age to life expectancy in 2006 and has legislated 70 by 2040 (as summarised;
  *unverified*).
- **What Linked gives in the model** (sketch, both sexes): 65 (the floor) in 1836 and 1950, 70 today, about 84 with
  era 11 medicine, about 108 with ageing at 0.75, and no pension age under immortality.
- **The minimum term** stays five years (parent §8.2).
- **UBI and Post-Scarcity**, the welfare group's later laws (`extra_laws.txt:285`, `:344`), replace Old Age Pension.
  Under them there is no pension age: the old are paid as everyone is, there is no separate pension bill, and the
  working ages end at capacity, with the after-pension share applied from the old-age threshold (§1.5's figure) as a
  stand-in for choosing leisure. Post-Scarcity's own −0.04 workforce line stays.
- **Events** that read "65+" (the parent's Greying of the Nation) read the pension age or the old-age threshold
  instead. Two late ones: **The Pension Without End** (pensioners pass half the people: link it, raise it or pay) and
  **The Last Generation?** (Biological Immortality; parent §9).

### 2.3 What an immortal society's workforce looks like

From the sketch (60 years after immortality, 1.6 children per woman):
- **Linked to Longevity**: nobody reaches the pension age; the workforce is 0.77 of all people, everyone not a child.
  The dependency ratio collapses to the children.
- **Standard (65)**: 67% of the people are pensioners and the workforce falls to 0.29 against today's 0.45. A
  leisure society paid for by a quarter of its people; it can be a choice, and Post-Scarcity is where the game puts
  it.
- **Without Old Age Pension**: as Linked; the old never tire.

### 2.4 Youth and dependency

The youth share falls under immortality as the adults pile up (the calendar 0–14 share is about half today's after
60 years). The youth bulge (calendar 20–29) disappears. Dependency becomes a choice made through the pension age, not a
fact of biology: exactly the parent's "ageing is mainly a fiscal problem", taken to its end.

## 3. Children: how many and when

### 3.1 Planned and unplanned births: the split the census already has

The census's fertility is wealth × natural × (1 − means × (1 − desired)) (`demographics_model.py:160`), which is the
sum of two parts:
- **Planned**: wealth × natural × means × desired, the families who choose their number;
- **Unplanned**: wealth × natural × (1 − means), the births the means don't reach.

**Proposal: planned births follow the calendar, unplanned births the body.**
- Planned births follow a schedule over calendar age, the stage of life at which people form families. Lifetime
  planned births equal the wanted number, however long people live.
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
- **Fecundity by biological age** multiplies planned births: births postponed past what the body allows are lost.
  Proposal: 1 to 30, 0.9 at 35, 0.7 at 40, 0.35 at 45, 0 from 50 (after Leridon 2004, *Human Reproduction*, as
  summarised; assisted reproduction recovers part of the loss, which a biotech tech could carry). So late
  postponement costs births, and life extension gives them back: a woman of 45 with the body of 35 has the child she
  postponed. That is the late game's answer to "when".
- **Phase 2 builds none of this** but keeps births computed as the two parts (§8.1).

### 3.3 How many: the completed-family bound (parent §13)

Under immortality, people after 50 years from today's structure, the body pulled 10% a year toward 35 (3% in
brackets); "lifetime" is the children so far of women aged 100 at year 50:

| Fertility reads | People after 50 years | Lifetime children | Variables a state |
|---|---|---|---|
| Calendar age for all births | ×1.19 (×1.17) | 1.60 | none |
| **Planned by calendar, unplanned by biology**, means 0.9 | ×1.40 (×1.30) | 1.99 | none |
| … means 0.95 (the cap) | ×1.30 (×1.23) | 1.80 | none |
| Biological age, with §13's children-so-far bound | ×1.45 (×1.34) | 2.06 | 30 (per band) to 150 |
| Biological age, no bound | ×2.29 (×1.86) | 3.69 and rising | none |

Every run starts at 1.6 children per woman over calendar 15–49. The split's unplanned part is 3.0 children (Rich
today's wealth and natural terms) × (1 − the means): 0.3 at means 0.9, so 1.3 are planned. The §13 row stops planned
births at 1.6 and keeps an unplanned 3.5 × 0.1.

- **The recommended split gives the bound §13 wanted for free.** Wanted families stay finite; the unplanned trickle
  goes on at about one child a century per woman at means 0.9 and half that at the cap, so §13's "slow trickle over
  centuries" is faster than §13 guessed, and the means matter more.
- **§13's children-so-far count** reaches almost the same numbers (planned births stop at the wanted size, unplanned
  go on), at 30–150 more variables. The calendar schedule does the counting.
- **Second families** (§13: "a higher wanted size brings a second family"): an optional planned tail at calendar
  50–100 for women whose bodies are fertile, switched on by a pronatalist measure under immortality. Not proposed for
  the first build.

### 3.4 The brake when deaths approach zero

- **In a rich, low-fertility state immortality turns decline into slow growth**: at 1.6 children per woman, ×0.75 in
  50 years with era 11 medicine alone becomes ×1.30–1.40 with the recommended split. A swing of about a point a year,
  not an explosion: births per 1,000 fall as the adults pile up while deaths fall from about 8 to 2.
- **A flat population needs low wanted fertility and near-perfect means, for good** (sketch, the pull at 3%, 60
  years): under the recommended split, 1.0 children per woman still grows ×1.20 at means 0.9 and ×1.10 at the cap
  (0.95), because rejuvenated women of every calendar age add the unplanned trickle; 0.8 children at the cap gives
  ×1.06. With every birth timed by the calendar, 1.0 children holds it at ×1.02. Before immortality the line was about
  2.1. So Population Control's late role is to hold both the wanted size and the means, permanently, not for a
  generation.
- **In a high-fertility state growth was already fast**: at 3 children per woman the sketch grows ×2.19 in 50 years
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

- **The census is per state.** It has one ring a state, so the treated and untreated share each cohort (§1.3). It can't
  give the treated their own age structure; the approximation is that they are spread like everyone else.
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

For wealth band k, access a_k is the larger of two routes; A is the people-weighted mean.

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

The augmentation laws already sort the strata this way (Unrestricted gives the upper strata SoL +5 and the lower −1),
so access needs no new law group. Alternative considered: a new law group for longevity care; rejected, since the
health and augmentation laws already say who gets medicine and enhancements.

### 4.3 The longevity gap, and who actually dies

- **The gap** is the difference in the chance of living to 100 between the treated and the untreated (two life
  tables, a step each). Points of a bounded figure, not years: under immortality the years are in the hundreds. The
  sketch's era 11 gap is 67% against 35% (32 points); under immortality 81% against 35%.
- **Today's gap, for scale:** the richest 1% of American men live 14.6 years longer than the poorest 1%, women 10.1
  (Chetty et al. 2016, *JAMA*); the census's Private Health Insurance line is the game's version.
- **Who dies in the engine.** The census fits a wealth slope to its bands each step: each band's death multiplier
  (1 − a_k × (1 − the treated's rate ÷ the untreated's)) against its wealth, people-weighted, and adds it to `te_dg_w`.
  M keeps the state's total right. Rich pops then really die less, grow relative to the poor and shift the strata.
  The floor of −0.005 a wealth level (`demographics_params.py:246`), which holds a wealth-99 pop at half the census's
  rate, must give way to a floor scaled by the treated's rate (§9, call 10).
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

### 5.1 The pension: money

- **Who is paid**: people at or above the pension age, under Old Age Pension (§2.2).
- **How much**: a weekly expense of GDP ÷ 52 × the pensioners' share × B, where B = 0.08 per level of Social Security
  (0.4 of GDP per head per pensioner at level 5). The mod's pattern: a static modifier with `country_expenses_add = 1`
  and a GDP-scaled multiplier (`scripting_best_practices.md`, "Expense Scaling with GDP"; `modifiers.log:595`).
- **Anchor**: OECD public pensions cost about 8% of GDP with about 18% of people over 65 (OECD, *Pensions at a Glance
  2023*, as summarised): about 0.4 of GDP per head per pensioner.
- **Sizes (sketch)**: rich today at 65, 31% pensioners → 12% of GDP; immortality at 65 → 27% and still rising;
  Linked to Longevity → near 0.
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
  under immortality is the expensive choice by design, and Linked to Longevity is the way out; The Pension Without End
  (§2.2) offers it.
- **AI**: picks the setting by the bill's share of its GDP and its treasury (the parent §11.2's rule), the same
  weights for every country.

## 6. The panel

### 6.1 What replaces life expectancy

| Candidate | Under immortality | Verdict |
|---|---|---|
| Life expectancy at birth | 559 years, or 129 cut at 150 | keep while under 100; then "100+" |
| Median age at death | 594 for women, 203 for men | no: it splits by sex on the external rates, and reads as nonsense |
| **Living to 100** | 81% | **yes**: bounded, readable in every era from 1836's 0% to now and on |
| **Old age from** (the age with 15 years left; Sanderson and Scherbov 2005, *Nature*, and 2010, *Science*) | none | **yes**: says what "old" means now, and drives Linked to Longevity |
| Deaths per 1,000 | 2.2 | already shown (realized); in the late game it is the honest figure |
| Healthy lifespan (years to biological 65) | unbounded | no: undefined under immortality |
| **Mean biological age** | 29 against a calendar mean in the hundreds | **yes**, from era 11 |

### 6.2 The rows

All "Label: value" with the breakdown on hover (style guide rules 1, 3, 5). Country figures are people-weighted over
the census states.

| Row | Section | Shown | Value | Hover |
|---|---|---|---|---|
| Life expectancy | Overview; state figures | always | `77`, then `100+` once the census's figure passes 100 | at birth and 65, women and men, the five causes (as built) |
| Old age from | Overview; state figures | phase 2 | `75`, or `none` | 15 years left; women and men; Linked to Longevity sets the pension age five years below it |
| Living to 100 | Overview; state figures | from era 11, or once 1% | `35%` | treated and untreated; women and men |
| Biological age | Overview; state figures | from era 11 | `38 (calendar 61)` | mean ages; the ageing rate; the pull; the treated share |
| Workforce | Work and Retirement (new, open) | phase 2 | `62% × 71% = 44%` | working-age share by its bounds; at work by sex and class mix; workers past the pension age |
| Pension age | Work and Retirement | Old Age Pension | `67 (Linked)` | the setting buttons sit beside it (rule 6); the old-age threshold |
| Pensioners | Work and Retirement | Old Age Pension | `18%` | |
| Pension bill | Work and Retirement | Old Age Pension | `£1.2M a week (6% of GDP)` | pensioners × B |
| Health need | Work and Retirement | phase 2 | `×1.8 of 1836` | by age band; medical technology; longevity care |
| Longevity care | Longevity (shown from era 11, rule 7) | era 11 | `42% of people` | by strata; the market threshold ("within reach from wealth 45"); the laws |
| Longevity gap | Longevity | era 11 | `32 points` | living to 100, treated and untreated; the approval and movement effects it drives |
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
- **History** adds Living to 100 from era 11 (optional).

## 7. Cost

| Item | Variables a state | When | Save (887 states, 60–85 bytes each) |
|---|---|---|---|
| Phase 2 figures: working-age share, share at work, pensioners, health need, old-age threshold | 5 | always | about 0.3 MB |
| Phase 3: A, r, pull, deficits (per band, up to 25, plus the pool), Living to 100 treated and untreated, mean biological age, access by strata (3), mean age at childbirth | up to 35 | era 11, states with A > 0 | about 2 MB |
| … with deficits per slot instead | up to 135 | | about 8 MB |
| §13's children-so-far (not recommended) | 30–150 more | | 2–9 MB |

Against about 345 a state today (360 with the Causes of Death plan). The country adds a handful (the pension age and
setting, the bill's multipliers, the gap).

**Time.** Phase 2's figures are sums the sweep already visits. Phase 3 doubles the rate work for the treated slots (a
lookup and a second rate a slot) and the life tables (treated and untreated): about 1 ms → 2 ms a state, on its own
day. The pop walk gains nothing: access reads the stored bands. Owner check 5 (the benchmark in a late-game save) is
the gate; per-band deficits keep the risk small.

## 8. Phasing

### 8.1 Decide now: what phase 2 builds so it doesn't bake in 1836

1. **Two indexes in the sweep.** Phase 2's new per-age sums (workers, pensioners, health need) read a biological index
   that is the calendar index until phase 3: one local per slot, no variable.
2. **The pension age is a country variable**, set by the setting; nothing compares with a literal 65. The four
   positions (§2.2) can ship with phase 2: Linked to Longevity needs only the old-age threshold, which the life table
   already allows.
3. **Participation is a table over ages** in `demographics_params` (working-age start by law, capacity by biological
   group, the after-pension share), not a 15–64 band.
4. **Health need is a weight table by biological group**, not a 65+ share.
5. **Births are computed as planned plus unplanned**, each with its own schedule (the same one in phase 2).
6. **The old-age threshold** is computed and stored at each step (a reverse pass over the life table's 31 groups).
7. **Names reserved**: `te_dg_d<j>` (deficits), `te_dg_treated`, `te_dg_age_rate`, `state_ageing_rate_add`,
   `state_rejuvenation_add`.

None of these changes a number in phase 2.

### 8.2 Phase 3

The ageing rate and its carriers; deficits; Biological Immortality's pull; access and the wealth slope; the longevity
gap and its politics; the two fertility schedules, postponement and fecundity; ectogenesis's share; the late display
rows; the late-era lines' move into the census (§8.4); the late check of adult external and work rates (§1.4).

### 8.3 Dependencies on work in flight

- **Causes of Death (#905)**: health-care access drifts; the public route of §4.2 reads the drifted access, and its
  medical-diffusion type speeds the market threshold. Its section gets the biological-age line (§6.2). No conflict.
- **Late Marriage and Birth Spacing (#906)**: their phase-3 blended schedules and §3.2's mean age at childbearing are
  one parameter; build it once, in phase 3.
- **#894's workforce from participation**: §2.1 is that model with capacity added as its upper bound when there is no
  pension; write it into the parent §7 with this draft's clocks.
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

## 9. Owner calls

1. **Two clocks**: planned births, pension eligibility, schooling and conscription read calendar age; deaths, capacity,
   health need and unplanned births read biological age (§0). This amends the parent §1's "every age-specific rate
   reads biological age". *Recommended.* Alternative: the parent's single clock with §13's bound.
2. **Phase 2 builds the interfaces in §8.1** (two indexes, a pension-age variable, participation and need tables,
   planned and unplanned births), changing no number. *Recommended.*
3. **Era 11's ageing rate: 0.75** (personalized medicine −0.15, genetic engineering −0.10; treated life expectancy about
   103). *Recommended.* Alternative: the parent's 0.5 (about 130, and an old-age threshold past the ring).
4. **Immortality's pull toward 35: 3% a year** (deaths per 1,000 from 8 to about 3.6 in ten years). *Recommended.*
   Alternative: 10% (2.4 in ten years).
5. **Fertility under immortality: planned by calendar, unplanned by biology**, no new variables; growth ×1.2–1.4 in 50
   years at 1.6 children (§3.3). *Recommended.* Alternatives: §13's children-so-far count (×1.3–1.45, 30–150 more
   variables), or biological age with no bound (×2.3 and rising).
6. **The pension setting: four positions**, Early 60, Standard 65, Raised 70 and Linked to Longevity (five years below
   the old-age threshold, never below 65, at most a year a year; 70 today). *Recommended.* Alternatives: three
   positions all linked (loses the 20th century's squeeze), or three calendar positions (an immortal society can't
   escape its bill).
7. **The workforce ratio's cap: 0.6** on the engine's scale. *Recommended*, since vanilla never passes 0.5. Alternative:
   no cap (immortality with no retirement reaches about 0.7).
8. **Deficit storage: per five-year birth band** (up to 25 variables a treated state). *Recommended.* Alternatives:
   per slot (up to 125; exact) or parametric (2; wrong at era 12).
9. **Access by law × wealth band × a falling market threshold**, through the existing health and augmentation laws
   (§4.2's table). *Recommended.* Alternatives: a new law group; access by health-care access alone (no rich-first).
10. **Rich pops really die less**: the census fits a wealth slope from its bands onto the existing Census: Deaths by
    Wealth pair, with a floor scaled to the treated's rate instead of −0.005 a level. *Recommended.* Alternative: the
    gap as display and politics only, every pop dying at the state's rate.
11. **The gap's politics**: Trade Unions and Rural Folk approval down to −3, Labor movement support up, both scaled by
    the gap and the lower strata's untreated share. *Recommended*, small. Alternative: none until a play-test asks.
12. **Pension money cost: GDP ÷ 52 × pensioners' share × 0.08 per Social Security level**. *Recommended.*
13. **Health bureaucracy: need by biological age (× 0.5, capped +1.0), +0.05 per chronic-treatment tech, +0.5 × the
    publicly covered longevity care.** *Recommended.*
14. **The panel**: Life expectancy shows `100+` past 100; add Old age from (phase 2), Living to 100 and Biological age
    (era 11); a Work and Retirement section that takes the pension setting from Family Policy; a Longevity subsection
    from era 11. *Recommended.*
15. **The late-era lines** move into the census under Full (§8.4): immortality as the ageing rate, Mental Health
    Awareness as external −10%, Mind Backups as external and work −50%; ectogenesis's births stay on top.
    *Recommended.*
16. **The adult external and work schedules get a 2000–2020 band in the harness** before phase 3, since under
    immortality they are the whole death rate (men's median age at death 203 against women's 594 in the sketch).
    *Recommended.*
