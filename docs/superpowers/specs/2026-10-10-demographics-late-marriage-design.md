# Demographics: late marriage and birth spacing — design

> **Status: design draft, 2026-10-10, second round.** It answers the owner call in step 2 of the phase 2 calibration
> plan (`docs/superpowers/plans/2026-10-10-demographics-phase2-calibration.md`, on PR #857): the census's children
> per woman run 4.3–6.1 where history's run 3.2–7.1. The cause is how marriage and childbearing were organised, and
> the game has no input for it. The first round chose between a strict late-marriage share and a broad one. The owner
> ruled (2026-10-10) that the two mechanisms are two practices, **Late Marriage** and a practice of low fertility
> within marriage, here **Birth Spacing**, and that they combine as a product. Parent spec:
> `2026-10-08-demographics-design.md` (§2.3 fertility, §13 Family Limitation as a general practice). No code here.
> Every number is a starting proposal the harness fits (§5). The fits in §2 were run offline on the gate run's 1837
> and 1887 saves with the census's own fertility function.

## Context

**The gap** (calibration plan, step 2; gate run, state by state, Gapminder's children per woman):

| Too high (model − history) | 1837 | 1887 | Too low | 1837 | 1887 |
|---|---|---|---|---|---|
| Denmark | +1.7 | +1.3 | Persia | −1.0 | −1.2 |
| Portugal | +1.4 | +1.4 | Turkey | −0.9 | −1.3 |
| Japan | +1.3 | +1.4 | Mexico | −0.8 | −1.3 |
| France (with Family Limitation) | +1.1 | +1.1 | Peru | – | −1.3 |
| Sweden | +1.1 | +0.8 | Russia | −1.0 | −0.7 |
| Britain | +1.0 | +0.2 | Argentina | −0.9 | −0.4 |

- The world average is right (5.95 and 5.74).
- In 1837 the census's wealth term gives every country 5.8–6.2 children, and its other terms barely separate them:
  the fertility factor runs 0.92–0.99 everywhere except France (0.80).
- Japan and Persia share SoL 6.6, and history has them at 4.5 against 7.1.

**The owner's rulings (binding, 2026-10-10).**
- **Practices, not laws.** Each practice is modelled like Family Limitation's planned general practice (§13): a
  share that starts from history, drifts with conditions and spreads from neighbours. Per state or per country is
  argued in §3.1.
- **Two practices for the two mechanisms:**
  - Late Marriage, the European pattern;
  - a practice of low fertility within marriage, for East Asia, Tokugawa Japan and India if the evidence supports
    it.
- **They combine as a product,** (1 − cut₁ × share₁) × (1 − cut₂ × share₂).
- **No targeting.** No country-specific mechanics, and no mechanic that names a culture or religion. A start value
  set from history by region is a start condition.
- **No law group for the 19th century:** these were customs, not policy. A 20th-century minimum marriage age is a
  possible later lever, in an existing law group (§6).

## 1. The history

Sources are cited by author and year; figures marked *unverified* were not checked against the original and must not
reach game text until they are.

### 1.1 Two ways to marry (Hajnal)

- **The north-western European pattern.** Hajnal (1965, "European Marriage Patterns in Perspective", in Glass and
  Eversley (eds.), *Population in History*) drew the line from Trieste to St Petersburg. West of it, women married in
  their mid-twenties and a large minority never married. Hajnal (1982, "Two Kinds of Preindustrial Household
  Formation System", *Population and Development Review* 8(3); also in Wall, Robin and Laslett (eds.), *Family Forms
  in Historic Europe*, 1983) set the criteria:
  - mean age at first marriage above 23 for women and above 26 for men;
  - a couple heads its own household on marriage;
  - before marriage the young spend years as servants in other households (for England, Kussmaul 1981, *Servants in
    Husbandry in Early Modern England*).
- **The joint-household pattern** (east of the line, and most of Asia, the Middle East and Latin America): women
  married before about 21 and men before 26. Young couples started in an older couple's household, and almost
  everyone married. In Korea practically every woman of 50 had married; for north-western Europe, summaries give 10%
  to 30% of women never married by 50 (Hajnal 1965, as summarised; *unverified*).
- **How far apart.** About half of women aged 15–49 were married at any time west of the line, about 70% east of it
  (Kertzer and Barbagli (eds.), *The History of the European Family*, 2001–03, as summarised; *unverified*). Ireland
  after the Famine went furthest: women married at 28–29 and about a quarter never married (Guinnane 1997, *The
  Vanishing Irish*; the figures as summarised, *unverified*).
- **It was a gradient, not a line.**
  - The Mediterranean married late men to younger women. Italy and southern Spain sat between the two patterns,
    while north-western Iberia (Galicia, Asturias, northern Portugal) was as late as the north, with high female
    celibacy (Reher 1998, "Family Ties in Western Europe: Persistent Contrasts", *Population and Development Review*
    24(2)).
  - In the east the Baltic provinces were western in type, and the Polish-Lithuanian lands mixed (Szołtysek 2015,
    *Rethinking East-Central Europe*).
- **It moved with the economy.** England's women married at about 26 around 1700 and about 23 by the 1830s, as wage
  work spread and real wages rose, and the change drove most of England's faster growth (Wrigley and Schofield 1981,
  *The Population History of England 1541–1871*; Wrigley, Davies, Oeppen and Schofield 1997, *English Population
  History from Family Reconstitution*; the ages approximate).
- **Why it arose** is argued:
  - women's wage work, in service and dairying, around the North Sea (De Moor and van Zanden 2010, "Girl Power",
    *Economic History Review* 63(1));
  - pastoral farming after the Black Death, which hired women (Voigtländer and Voth 2013, "How the West 'Invented'
    Fertility Restriction", *American Economic Review* 103(6));
  - impartible inheritance, where only one heir could marry onto the farm (Habakkuk 1955, "Family Structure and
    Economic Change in Nineteenth-Century Europe", *Journal of Economic History* 15(1)). Berkner and Mendels (1978,
    in Tilly (ed.), *Historical Studies of Changing Fertility*) found the inheritance link weaker than Habakkuk
    claimed.
  - Dennison and Ogilvie (2014, "Does the European Marriage Pattern Explain Economic Growth?", *Journal of Economic
    History* 74(3)) warn against reading too much into it: the pattern was strongest in some slow-growing places.

### 1.2 What marriage and spacing did to births

- **The Princeton indices** split overall fertility into the share of women married (Im) and the fertility of the
  married (Ig): with few births outside marriage, overall fertility ≈ Im × Ig (Coale and Watkins (eds.) 1986, *The
  Decline of Fertility in Europe*, with Coale and Treadway's provincial tables).
- **Bongaarts** (1978, "A Framework for Analyzing the Proximate Determinants of Fertility", *Population and
  Development Review* 4(1)) writes fertility as a product of indices: marriage, contraception, induced abortion and
  post-partum infecundity (breastfeeding and abstinence). Each enters as its own multiplier.
  - Late Marriage is his marriage index.
  - Birth Spacing gathers what the census lacks of the other three, in their customary forms: long breastfeeding and
    abstinence, abortion, and (for births the census counts, since infants killed at birth never join a cohort)
    infanticide.
- **Late Marriage's size.** Half married against 70% is a ratio of about 0.7. Gapminder's 1837 figures give the
  same:
  - north-western Europe (Denmark 4.0, Sweden 4.4, Britain 4.8, Germany 4.9, Belgium 5.0, the Netherlands 5.1)
    averages about 4.7;
  - the early-marrying high-fertility group (Russia 7.0, Persia 7.1, Turkey 6.9, Mexico and Argentina 6.8) averages
    about 6.9.
  - The ratio is 0.68.
- **Malthus** called delayed marriage the preventive check: "moral restraint" (*An Essay on the Principle of
  Population*, 2nd ed., 1803). Lee and Wang Feng (1999) argue that China had its own preventive check within
  marriage (§1.4).

### 1.3 Tokugawa Japan: Birth Spacing, not Late Marriage

- **Marriage was nearly universal by 30.** Women's age at first marriage ranged by region from about 14 to 25, lowest
  in the north-east, and divorce and remarriage were common (Kurosu and Takahashi, IUSSP paper; Tsuya, Wang, Alter,
  Lee et al. 2010, *Prudence and Pressure*). Some central and western villages reached Hajnal's age of 23, but none
  had his lifelong celibacy, and the north-east married in the mid-teens.
- **The families were small through low marital fertility:** long spacing, early stopping, abortion and infanticide
  (*mabiki*) (Hanley and Yamamura 1977, *Economic and Demographic Change in Preindustrial Japan, 1600–1868*; Smith
  1977, *Nakahara*; Drixler 2013, *Mabiki: Infanticide and Population Growth in Eastern Japan, 1660–1950*).
- **Succession went to a single heir** in a stem family, the *ie* (Saito 2000, "Marriage, Family Labour and the Stem
  Family Household", *Continuity and Change* 15(1)). The mod already starts Japan on Primogeniture
  (`common/history/extra_history.txt`).
- **Under Meiji fertility rose,** as the state suppressed infanticide and abortion (Drixler 2013). Gapminder has
  Japan at 3.6 in 1880, 4.7 in 1900 and 5.2 in 1911.
- **So Japan belongs to Birth Spacing,** at the practice's full value, and starts at 0 in Late Marriage (§3.3).
  - Starting both (Late Marriage 0.3 and Birth Spacing 0.8) gives the same children per woman: 4.39 / 4.15 against
    4.38 / 4.13.
  - The regional marriage ages don't justify the second practice, so the simpler start is recommended (§7, call 3).

### 1.4 The early-marrying world was not one place

- **Russia:** early and universal marriage, with about 7 children per woman in the late 19th century (Coale,
  Anderson and Härm 1979, *Human Fertility in Russia since the Nineteenth Century*).
- **China:** female marriage was early and near universal, but marital fertility was low, from late starting, long
  spacing, early stopping and female infanticide; many men never married (Lee and Wang Feng 1999, *One Quarter of
  Humanity*). Wolf and Engelen (2008, *Journal of Interdisciplinary History*) dispute how low it was. This is Birth
  Spacing.
- **India: the evidence supports the level, not yet the mechanism.**
  - Girls married very young: the Child Marriage Restraint Act of 1929 set the minimum at 14.
  - Gapminder's series is a flat 5.95 to 1880 (a guess), then follows the censuses: 5.92 in 1881, 5.79 in 1885, 5.73
    in 1900. That is about a child below Russia's data-based 6.6–7.0, at much the same game inputs.
  - The usual explanations are long breastfeeding, post-partum abstinence, widowhood without remarriage and poor
    health (*unverified here*). The first two are Birth Spacing's mechanisms; widowhood would be an exposure term
    like Late Marriage's.
  - So India starts in Birth Spacing at the level its census-era anchor needs, flagged as resting on the anchor
    (§7, call 2).
- **Korea:** universal early marriage (Hajnal 1965). Nothing here on its marital fertility: Gapminder has a flat
  guess of 6.0. It takes East Asia's start value as geography, *unverified*.
- **So "early marriage" alone puts China and India too high.** History's early-marrying societies span 5.5 (China) to
  7.1 (Persia). The game's inputs can't tell them apart: China (SoL 7.2, literacy 0.13), India (7.9, 0.19), Russia
  (8.0, 0.14) and Persia (6.6, 0.09) in the 1837 save. That is what the second practice is for (§2.2).

### 1.5 Spread and erosion

- **Late Marriage held through the 19th century.** Europe's fertility fell through marital fertility, not
  marriage. Nuptiality changed little, and rose in places, as birth control within marriage spread (Coale and Watkins
  1986; Watkins 1991, *From Provinces into Nations*).
- **The marriage boom, 1930s–60s.** Across the West ages at marriage fell and nearly everyone married, which fed the
  baby boom (Hajnal 1953, "Age at Marriage and Proportions Marrying", *Population Studies* 7(2)). Provincial
  differences in marriage narrowed (Watkins 1991). A common reading, not a settled result: once couples could limit
  births within marriage, they no longer had to wait to marry.
- **Customary spacing eroded before contraception arrived.** In Meiji Japan the state's suppression of infanticide
  and abortion raised fertility by about a child within a generation (Drixler 2013; §1.3). Fertility often rose
  before it fell elsewhere too, as breastfeeding and abstinence shortened (Dyson and Murphy 1985, "The Onset of
  Fertility Transition", *Population and Development Review* 11(3); *unverified here*). Modern contraception then
  replaced what custom had done.
- **After 1970: later and less marriage.**
  - In the north and west, cohabitation decoupled births from marriage (Lesthaeghe 2010, "The Unfolding Story of the
    Second Demographic Transition", *Population and Development Review* 36(2)).
  - In East Asia births stayed in marriage, so later and less marriage drove most of the fall (Retherford, Ogawa and
    Matsukura 2001, "Late Marriage and Less Marriage in Japan", *Population and Development Review* 27(1)).
- **Outside Europe** ages at marriage rose from the mid-20th century, with schooling and with law:
  - India raised its minimum ages to 15 for girls in 1949, and to 18 for girls and 21 for boys in 1978;
  - China's Marriage Law of 1950 set 18 and 20, its law of 1980 set 20 and 22, and the 1970s campaign *wan, xi, shao*
    ("later, longer, fewer") began with later marriage.
  - East of the Hajnal line early marriage lasted through the socialist period and gave way after 1990
    (*unverified here*).

### 1.6 How far to trust the anchors

- **Where the numbers come from.** Gapminder's children per woman before 1950 is Mattias Lindgren's compilation of
  published estimates, filled with Gapminder's own guesses where none exist. It is blended into the UN's series over
  1930–1970 (Gapminder documentation gd008).
- **Flat series are guesses:** China 5.5, Persia 7.08, Turkey 6.92, Mexico 6.80, Peru 6.82, Korea 6.0, and India
  before 1881, each unchanged for decades.
- **Data-based series:** the Western series rest on registration, and India's from 1881 on its censuses. They carry
  more weight than the guesses.

## 2. The model term

### 2.1 Where it acts (decided)

Today (`demographics_model.fertility`): children per woman = wealth × factor, with factor = 1 − means × (1 − desired).
With the two practices (owner, 2026-10-10):

    marriage = 1 − LATE_MARRIAGE_CUT × late marriage share
    spacing  = 1 − BIRTH_SPACING_CUT × birth spacing share
    children per woman = wealth × factor × marriage × spacing

- **Both act outside the means.**
  - Anything in `desired` is scaled by the means. An 1836 state's means are 0.15–0.27 (France, with Family
    Limitation, apart), so a term there would barely show in 1836.
  - Both customs did their work with no contraception at all.
  - The means are the share of couples who limit births by choice toward a desired size, which is Family
    Limitation's channel. Late marriage limits years of exposure; customary spacing limits births whatever size the
    couple wants.
- **A product, as the owner decided.** It is Coale's Im × Ig and Bongaarts's product of indices, and it stays between
  0 and 1 whatever the shares.
  - A plain sum gives nearly the same result at these cut sizes. It is identical on the gate saves, where no state
    starts with both practices, and lower by cut₁ × cut₂ × share₁ × share₂ where drift or spread brings both into one
    state: 0.03 at shares of 0.5 and 0.6, 0.10 with both full.
- **The known approximation.** A couple that limits births by choice and also marries late or spaces by custom
  compounds the brakes, where in reality one can make another redundant. That error is largest once the means are
  high, which is when the drift has lowered both shares (§4).
- **The panel's fertility hover** gains two lines beside wealth, education, child survival, urban life and means:
  "Late marriage ×0.70" and "Birth spacing ×0.66".

### 2.2 Size: the raise and the two cuts

Three numbers move together:
- **the baseline:** the wealth curve, `WEALTH_TFR_LOW` (6.2 today) and `WEALTH_TFR_HIGH` (3.5), scaled together by
  s, so that societies with neither practice reach history's 7;
- **Late Marriage's cut**, at a full share;
- **Birth Spacing's cut**, at a full share. Tokugawa Japan is the full share, 1.0.

**Why a second practice is needed.**
- A raise of 15% with no second practice lifts China to 7.0 (history 5.5) and India to 6.9 (6.0).
- China's births ×1.15 add about 0.5% a year to its growth (ln 1.15 ÷ 29), which undoes step 1's fit. That fit set
  the poverty term so that China grows +0.3% a year in 1887, Maddison's peacetime pace.
- Birth Spacing gives East and South Asia their own brake, so the raise can bring the Middle East, Russia and Latin
  America to 7 while China and India hold.

**China's and India's start: held, not history.**
- Their Birth Spacing start is the value that cancels the raise: share = (1 − 1/s) ÷ cut₂, 0.38 at the proposal.
  China's children per woman and growth then stay where step 1 fitted them.
- China at history's 5.5 needs a share of 0.63. Its growth in 1887 then falls from +0.32% to −0.04% a year, and the
  world's from +1.03% to +0.91%. That waits for the joint mortality refit (§2.4); if the refit raises China's life
  expectancy, the share can rise with it.

### 2.3 The fit

**Method.**
- Each state's own inputs from the gate saves (SoL, literacy, urban share, crowding, its owner's techs and laws),
  through `demographics_save_inputs.state_inputs` and `demographics_harness.inputs_for` on PR #857's branch.
  - The saves are `autosave.1791572508.v3` (1837) and `autosave.1791583167.v3` (1887) in
    `/mnt/d/vic3te-data/vic3te-demog-gate-data/saves/`.
  - The anchors are the step-2 CSV (`/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv`).
- Each state's two shares come from the start tables in §3.2 and §3.3, then × s × (1 − cut₁ × share₁) × (1 − cut₂ ×
  share₂).
- A country's figure is its states' weighted by people, over its home strategic regions (those holding 10% or more
  of its people), so that colonies don't count.
- The anchor is Gapminder's children per woman within 5 years of the save.
- Dropped as not marriage or spacing: the Netherlands in 1887 (it shrank to its colonies in that game), and the USA
  and Chile in 1887 (fertility transitions; for the USA, the land-availability decline, Easterlin 1976, *Journal of
  Economic History* 36(1)).
- For each s, the cuts minimise the root-mean-square error over the anchor countries, with China and India held.

**Against today and the first round's options:**

| | Wealth curve × | Cuts | Error | World children per woman 1837 / 1887 | World growth, % a year | Persia, Turkey, Russia, Mexico, Argentina 1837 |
|---|---|---|---|---|---|---|
| Today | 1 | – | 0.89 | 5.96 / 5.74 | +1.08 / +0.98 | 5.9–6.05 |
| First round S (strict late marriage only) | 1.04 | 0.26 | 0.60 | 5.94 / 5.78 | +1.04 / +0.96 | 6.1–6.3 |
| First round B (one broad share) | 1.15 | 0.32 | 0.49 | 6.03 / 5.89 | +1.08 / +1.03 | 6.7–7.0 |
| Two practices, s 1.10 | 1.10 | 0.26, 0.30 | 0.49 | 5.95 / 5.80 | +1.05 / +0.98 | 6.5–6.7 |
| Two practices, s 1.12 | 1.12 | 0.28, 0.32 | 0.48 | 5.98 / 5.83 | +1.06 / +1.00 | 6.6–6.8 |
| **Two practices, s 1.15 (proposed)** | 1.15 | **0.30, 0.34** | 0.49 | 6.04 / 5.89 | +1.09 / +1.03 | **6.7–7.0** |
| Two practices, s 1.18 | 1.18 | 0.32, 0.36 | 0.53 | 6.08 / 5.94 | +1.11 / +1.06 | 6.9–7.1 |

- **The proposal is s = 1.15:** it is the raise that brings the high-fertility group to about 7, at an error within
  0.01 of the best. Late Marriage's cut is 0.30 (×0.70 at a full share) and Birth Spacing's 0.34 (×0.66).
- **It matches the first round's B at the same raise.** What changes is that Japan and China now sit in a practice
  that describes them, and Late Marriage can show a real age (§5.3).

**Country by country** (children per woman, 1837 / 1887; "–" where the save or the anchor has none):

| Country | Late Marriage, Birth Spacing shares | Model today | Two practices | History (Gapminder) |
|---|---|---|---|---|
| Britain | 1.0, 0 | 5.78 / 4.39 | 4.66 / 3.54 | 4.79 / 4.24 |
| France | 1.0, 0 | 4.62 / 4.26 | 3.73 / 3.43 | 3.60 / 3.22 |
| Germany (Prussia) | 0.95, 0 | 5.59 / – | 4.59 / – | 4.90 / – |
| Sweden | 1.0, 0 | 5.52 / 5.19 | 4.44 / 4.18 | 4.37 / 4.36 |
| Denmark | 0.8 / 0.44 (colonies), 0 | 5.70 / 5.62 | 5.01 / 5.51 | 4.04 / 4.28 |
| Belgium | 1.0, 0 | 5.57 / 4.68 | 4.48 / 3.77 | 4.98 / 4.36 |
| Netherlands | 1.0, 0 | 5.54 / – | 4.46 / – | 5.11 / – |
| Austria | 0.67 / 0.57, 0 | 5.79 / 5.62 | 5.32 / 5.35 | 5.10 / 4.49 |
| Spain | 0.70, 0 | 5.85 / 5.47 | 5.32 / 4.97 | 5.13 / 4.78 |
| Portugal | 0.69 / 0.60, 0 | 5.85 / 5.68 | 5.36 / 5.14 | 4.50 / 4.38 |
| Italy (Sardinia) | 0.5–0.6, 0 | 5.69 / 4.89 | 5.39 / 4.67 | 5.47 / 5.03 |
| Japan | 0, 1.0 | 5.75 / 5.43 | 4.38 / 4.13 | 4.54 / 4.04 |
| China | 0, 0.38 | 6.09 / 6.03 | 6.10 / 6.04 | 5.50 / 5.50 |
| India | 0, 0.38 | 6.02 / 5.85 | 6.03 / 5.86 | 5.95 / 5.76 |
| Russia | 0.07, 0 | 6.00 / 5.85 | 6.74 / 6.61 | 7.00 / 6.61 |
| Turkey | 0, 0 | 6.04 / 5.57 | 6.95 / 6.41 | 6.92 / 6.92 |
| Persia | 0, 0 | 6.05 / 5.93 | 6.96 / 6.81 | 7.08 / 7.08 |
| Egypt | 0, 0 | 6.00 / 5.71 | 6.90 / 6.57 | 6.05 / 6.03 |
| Mexico | 0, 0 | 5.99 / 5.46 | 6.89 / 6.28 | 6.80 / 6.80 |
| Brazil | 0, 0 | 5.92 / 5.50 | 6.80 / 6.33 | 6.26 / 6.24 |
| Argentina | 0, 0 | 5.92 / 5.72 | 6.81 / 6.58 | 6.80 / 6.14 |
| Peru | 0, 0 | – / 5.51 | – / 6.34 | – / 6.82 |
| USA (1837 only) | 0, 0 | 5.56 | 6.39 | 6.24 |

**What is left, and why:**
- **Denmark and Portugal** stay 0.8–1.2 high. The cause is their colonies, not their customs: 19% of Denmark's people
  in 1837 and 36% in 1887 live in West Africa at share 0, and the home-region filter keeps them. The harness needs an
  incorporated-state filter (§5.1).
- **Belgium and the Netherlands** fall 0.5–0.7 low. They married as late as anyone; their marital fertility was
  high. That is a different term, not these.
- **Britain in 1887** falls 0.7 low. The census's education, urban and means terms already bring Britain down by
  1887, and Late Marriage compounds them, where historically Britain's marital fertility had only begun to fall.
  The stage-2 means fit (vulcanization +0.20, feminism +0.15) was made with no marriage term, so it carries part of
  the West's level. It is refit in step 2 (§5.1).
- **Egypt** rises 0.5–0.9 high and Brazil up to 0.5. Their anchors are guesses near 6.
- **China** stays 0.6 high, held at the level step 1's growth fit needs (§2.2), against a flat guess of 5.5.

### 2.4 What the fix does to growth: step 2 must refit step 1's mortality

Births that match history expose deaths that don't. The table compares the model's steady growth from each
country's own rates (the harness's growth, ln(daughters per woman) ÷ 29) with history's (Maddison's population
through Clio Infra, migration included), in % a year, 1837 / 1887:

| | Today | Two practices | History |
|---|---|---|---|
| Britain | +1.42 / +1.11 | +0.67 / +0.36 | +1.03 / +0.79 |
| Belgium | +1.60 / +1.38 | +0.85 / +0.63 | +0.84 / +0.95 |
| Sweden | +1.54 / +1.70 | +0.80 / +0.95 | +0.82 / +0.44 |
| France | +0.98 / +0.80 | +0.24 / +0.06 | +0.47 / +0.25 |
| Japan | +0.90 / +0.80 | −0.05 / −0.15 | +0.11 / +0.85 |
| Persia | +0.76 / +1.38 | +1.24 / +1.86 | +0.45 / +0.34 |
| Mexico | +1.27 / +1.60 | +1.75 / +2.09 | +0.99 / +1.20 |
| Russia | +1.32 / +1.36 | +1.72 / +1.78 | – |
| China | +0.89 / +0.32 | +0.90 / +0.32 | +0.07 / +0.32 |
| India | +1.22 / +1.38 | +1.23 / +1.38 | +0.40 / +0.84 |
| World | +1.08 / +0.98 | +1.09 / +1.03 | |

- **The West grows too slowly** because its deaths are too high. Britain's life expectancy reads 36 in 1837
  (history 41) and Denmark's 34 (41.5): the cost step 1's poverty term put on the West.
- **Japan shrinks.** That is near the late Tokugawa stagnation (+0.1%) in 1837 but far from Meiji's +0.85% in 1887.
  The census reads Japan at SoL 6.4, so the poverty term holds its life expectancy at 31 (history 37).
- **The Middle East and Latin America grow too fast** because their deaths are too low. Step 1 found Mexico at 40
  against history's 23 in the 1890s.
- **India grows too fast already**, at +1.4% against +0.8%. Birth Spacing holds it there; step 3's work on India
  covers the rest.
- **The world line hardly moves.**

**So step 2 can't be closed on fertility alone.** Once births are right, step 1's mortality fit has to be refit on
the same saves, against life expectancy and growth together (§5.1, §5.2). The countries that matter most are
Britain, Belgium, Japan, Persia and Mexico.

### 2.5 What else it touches

- **Maternal deaths** fall with births, per birth, as now. Nothing to add.
- **Age at first birth and the cohort ring.**
  - The census's age schedule (`ASFR_SHAPE_BY_GROUP`, 6% of births at 15–19 and a peak at 25–29) is already a
    late-marrying one, and every state uses it.
  - A state without Late Marriage has more births at 15–24 and a mean age at childbearing near 27 instead of the
    schedule's 30, so a shorter generation. At the same daughters per woman it grows about 0.1% a year faster (ln 1.4
    over 28 years against 30).
  - Birth Spacing's early stopping lowers births at 35–49 a little.
  - The fix is schedules blended by the shares, with `growth_factor`'s generation length (29 years, fixed today)
    following the blend.
  - **Not in phase 2:** the effect is second-order, and the seed and replay would both change. Phase 3, beside the
    sex-balance effects.
- **Women's work before marriage** (years as servants) and the female share of labour migrants (parent §2.5) could
  read Late Marriage's share. Not proposed: neither changes a decision now.
- **Births outside marriage** are not modelled. Late Marriage's share counts births that waited for marriage; after
  1970 that stops being true in the north-west (§4.2).

## 3. Scope and start values

### 3.1 Per state, not per country

**Recommended: per state, for both practices.**
- **The Hajnal line runs through countries.** It splits the game's Austria (people-weighted share 0.57–0.67 in the
  fit), Prussia (Rhineland and East Prussia against Posen), Russia (the Baltic provinces against the core), Spain and
  Portugal (north against south) and Italy. A national share blurs exactly the states the fit separates.
- **Spread crosses borders.** It runs from state to state: France to Wallonia, Prussia to Posen.
  `every_neighbouring_state` iterates from state scope (`docs/engine/effects_summary.txt`; the mod already uses
  `any_neighbouring_state`).
- **The drivers are state inputs.** The agrarian share and women's job share come from the census's yearly walk
  (`te_dg_agr_share`, `te_dg_fjob_share`). Laws read through `owner`, as every census input does.
- **Cost:** two variables a state, against the ring's 345, and one neighbour walk a year.
- **The country** shows each practice's people-weighted mean, as it does for children per woman.

Family Limitation's §13 proposal is national. Building all three on one per-state practice is §7, call 7.

### 3.2 Late Marriage's start table

- **Where the values come from.** The generator writes them from a table in `demographics_params.py`. Each is set by
  strategic region, with state regions overriding where the line or the Mediterranean gradient cuts through.
- **How the script reads them:** `region = sr:region_x` (used in `common/power_bloc_names/extra_power_bloc_names.txt`)
  and `state_region = s:STATE_X` (used in `common/buildings/extra_buildings.txt`).
- The shares are geography, not culture.

| Where | Share | Basis |
|---|---|---|
| `region_western_europe` (Britain, Ireland, northern France, the Low Countries, Rhineland) | 1.0 | Hajnal's core |
| `region_northern_europe` (Scandinavia, Finland, Iceland) | 1.0; Kola and East Karelia 0.2 | Hajnal; Finland's east was mixed |
| `region_central_europe` (Germany, Switzerland, Austria, Bohemia) | 1.0 | Hajnal |
| Occitania (Provence, Guyenne, Languedoc, Aquitaine, Rhône, Savoy, Auvergne-Limousin) | 1.0 | France |
| North-western Iberia (Galicia, Asturias, Basque Country, León, Old Castile, Entre Douro e Minho, Beira, Estremadura, Azores, Madeira) | 0.9 | Reher 1998: late, with high female celibacy |
| The rest of Iberia | 0.6 | Reher 1998 |
| Italy (every Italian state region) | 0.5 | Reher 1998: the Mediterranean between the two |
| Baltic provinces, East and West Prussia, Posen, Greater Poland, Slovenia | 0.8 | Szołtysek 2015; west of the line |
| Mazovia, Lesser Poland, West Galicia, Kaunas, Vilnius, Croatia, Transdanubia, Slovakia | 0.4 | the gradient |
| Everywhere else, Japan included (Russia, the Balkans, the Middle East, Africa, the Americas, Asia) | 0 | early, universal marriage |

- **Settler colonies start at 0** (the USA married young and universally in the 1830s) and take the share their
  neighbours and conditions give them.
- **Ireland** starts at 1.0 with Britain. Pre-Famine Ireland married earlier (women about 24), but the post-Famine
  rise isn't a driver this design has, so 1.0 sits between the two.

### 3.3 Birth Spacing's start table

The same generator, read the same way. The share's 1.0 is Tokugawa Japan's restraint.

| Where | Share | Basis |
|---|---|---|
| Japan's state regions (Hokkaido to Kyushu, Ryukyu excepted) | 1.0 | §1.3: Hanley and Yamamura; Drixler |
| `region_north_china`, `region_south_china` | 0.38 | §1.4: Lee and Wang Feng. Held at today's level (§2.2); 0.63 would reach Gapminder's 5.5 |
| Manchuria and Korea (Southern and Northern Manchuria, Shengjing, Seoul, Busan, Sariwon, Pyongyang, Yangho) | 0.38 | East Asia's value as geography; *unverified*, no anchor |
| `region_north_india`, `region_south_india` | 0.38 | §1.4: the census-era anchor; mechanism *unverified* |
| Everywhere else | 0 | |

- **India at 0 instead:** it reads 6.92 / 6.73 against history's 5.95 / 5.76 and grows +1.86% a year in 1887
  (history +0.84%). The error rises from 0.49 to 0.55, and the world moves to 6.18 / 6.03 and +1.17 / +1.11% a year
  (§7, call 2).
- **Neither table names a culture or religion.** India's start rests on its anchor, not on anyone's customs by name,
  and the practice's text describes what it does (fewer births, further apart), as the family-policy measures' text
  does (parent §8.1).

### 3.4 Seeding

- **1836:** each state takes both table values at its first census (`te_demog_seed`). Nothing jumps on day one: the
  births modifier isn't applied until phase 2.
- **A state with no share** (new, split, or from an older save) takes the people-weighted mean of its neighbours
  that have one, else its table value. A split state is the same people as its sibling.
- **Revolutions:** the shares are state variables, so they stay (`scripting_best_practices.md` § "What a Civil
  War's Winner Inherits").

## 4. Drift and spread

### 4.1 Late Marriage's drivers

Each is checked against history and against the game. The keys named exist in `common/` or `vanilla_parsed/`.

| Candidate | History | Game input | Verdict |
|---|---|---|---|
| **Impartible inheritance, undivided farms** | One heir marries onto the farm and the rest wait or never marry. Strongest in post-Famine Ireland (Guinnane 1997) and the Alpine stem-family regions. Habakkuk 1955 for, Berkner and Mendels 1978 for weaker | `law_primogeniture`, or `te_inh_has_undivided_farms` (Undivided Farm Succession, `amendment_undivided_farm_succession`), × `te_dg_agr_share` | **Use**, raising the share, small. Forced Heirship (`law_equal_inheritance`) and Customary (`law_partible`) add nothing: their effect on births belongs to Family Limitation (§13) |
| **Women's paid work before marriage** | Service and dairying held North Sea marriage late (De Moor and van Zanden 2010; Voigtländer and Voth 2013); in the 20th century, women's jobs delayed marriage outside Europe | `te_dg_fjob_share` (light industry, services, urban facilities) × `te_demog_female_work_share` ÷ 0.48, the law's women's work share at its fullest | **Use**, raising the share. Near 0 in 1836 (No Women's Rights), up to about +0.15 in a modern economy |
| **Contraception** | Once couples limit births within marriage they needn't delay it: nuptiality rose in places as birth control spread, and the marriage boom followed (§1.5; a reading, not a settled result) | `state_contraception_add` × the census's access (0.3 + 0.7 × literacy): the means beyond traditional methods | **Use**, lowering the share. This is how the 20th century erodes the pattern, and it needs no new input |
| Schooling and literacy | Ambiguous: literate Scandinavia married late, the literate West of the 1950s married young, and schooling delays marriage in the 20th-century developing world | `te_dg_lit` | **Don't use.** Literacy already lowers fertility twice in the census (desired, and access to the means). Its 20th-century effect on marriage comes in through the later lever (§6) |
| Urbanisation | North-western towns had late marriage and much celibacy; eastern and Asian towns didn't | `te_dg_urban_share` | **Don't use.** It is already in `desired`, and its sign depends on the start pattern |
| Wage labour | Proletarians needn't wait for a farm: England's falling age at marriage, 1700–1830 (Wrigley et al. 1997). Lowers the share | none: the walk has `te_dg_agr_share` (Peasants and Farmers), not a wage-earner share | **Not now.** It needs one more sum in the pop walk, and its 19th-century effect in the West was small |
| Servants | Life-cycle service was the pattern's backbone (Hajnal 1982; Kussmaul 1981) | no pop type | **Can't.** Women's paid work above covers part of it |
| Prosperity (SoL) | Real wages moved English marriage (Wrigley and Schofield 1981), and the 1950s boom came with rising incomes | `te_dg_sol` | **Don't use.** SoL is already the wealth term, and as a driver it would push the opposite way to it |

### 4.2 Late Marriage's target and rates

Each year, on the state pulse, after the walk and before the fertility term:

    target = clamp(start × (1 − erosion) + inheritance + women's work, 0, 1)
    erosion = 0.7 × clamp((contraception − 0.1) / 0.2, 0, 1)
    contraception = state_contraception_add × (0.3 + 0.7 × literacy)
    inheritance = 0.15 × agrarian share, under Primogeniture or with Undivided Farm Succession
    women's work = 0.3 × women's job share × women's work share ÷ 0.48
    share += 0.025 × (target − share) + 0.005 × (neighbours' mean − share)

The neighbour term arrives in phase 3 (§4.4, §5.3); phase 2 builds the rest.

- **The start value is part of the target.** It is the custom, and it holds while conditions are 1836's. Without it
  the target would drift every state toward what its conditions say from the first year, and the game's conditions
  can't tell Denmark from Russia.
- **The rate, 2.5% of the gap a year,** is a half-life of about 28 years, a generation. The marriage boom moved
  Western women's age at marriage about 3 years in 25 years, about 0.4 of the share's range: 2–3% a year of a gap of
  0.7.
- **What it gives**, to be checked in the harness (§5):
  - the West holds 1.0 until its era-3 contraception (vulcanization, feminism) reaches a literate population. There
    the means beyond traditional methods reach 0.29, and the target falls to about 0.45;
  - so about 0.75 a generation later (1900 if the pair arrives around 1880), about 0.5 by 1950, and about 0.45 once
    women's jobs and the Pill are in;
  - early-marrying states rise only as women's jobs and laws arrive;
  - Japan and Britain, on Primogeniture, gain up to about 0.13 from the inheritance term on their farms.
- **The timing is the weak point.**
  - History's marriage boom came in the 1930s–60s, two generations after the era-3 methods. The drift starts the
    erosion when the methods spread, so the West's share runs about 0.2 below history's around 1900: Britain 1900
    reads 3.4 children against 3.1 at a full share and history's 3.5.
  - A later trigger (the means beyond 0.35, which needs the Pill) would hold the share longer and erode it faster.
    The harness compares the two.
- **After 1970** the share counts births that waited for marriage. Cohabitation decoupled the two in the north-west,
  so a falling share there is right even though real ages at marriage rose again. East Asia's later and less marriage
  after 1975 (Retherford et al. 2001) isn't produced by these drivers. The later lever (§6) and the means can give it.

### 4.3 Birth Spacing: custom that erodes

**What the game can support, honestly.**
- The practice's mechanisms have no input in the game: breastfeeding, post-partum abstinence, abortion and
  infanticide.
- No law, building or pop figure separates China from Persia (§1.4).
- **So Birth Spacing is custom: its start value, eroded by modernisation and contraception.** Nothing in the game
  builds it up, and the design adds no driver for it. A state gains it only from neighbours (phase 3), slowly.

**The two erosions the game can read:**
- **Contraception**, with the same term as Late Marriage's: modern methods replace customary ones (§1.5). Births then
  follow the means and `desired`, which the census already models.
- **Modernisation before contraception**, the Meiji rise (§1.5). The nearest input is health-care access
  (`state_health_care_access_add`, the census's own access line from the health laws' `institution_modifier`):
  midwives, registration and medicine reaching the people.
  - It is a proxy, not the mechanism. The state that registers births and licenses midwives is the state that ends
    infanticide and shortens customary abstinence, but the game has no line for either.
  - Fertility then rises before it falls, as in Meiji Japan. A player who builds a health system before contraception
    sees more births, which is history's order.

**The formulas:**

    target = start × (1 − erosion), with
    erosion = clamp(0.7 × clamp((contraception − 0.1) / 0.2, 0, 1) + 0.3 × clamp(health access line / 0.5, 0, 1), 0, 1)
    share += 0.025 × (target − share) + 0.005 × (neighbours' mean − share)

- **What it gives:** Japan's share falls toward 0.7 under a five-level health system before contraception: +15%
  births, about two-thirds of a child. Under the Pill era's means it falls toward 0.
- **Meiji's rise was faster,** about a child within a generation (§1.3). A state law against infanticide would be a
  sharper lever, but the game has none, and adding one would be a country-shaped mechanic.
- **Contraception only** (no health-access term) is the simpler alternative. It loses the Meiji rise (§7, call 5).

### 4.4 Spread from neighbours

- **As Family Limitation's §13 proposal does it:** each state closes part of the gap to its neighbours' mean,
  weighted by people (`every_neighbouring_state`), for each practice.
- **Kept slow, 0.5% a year,** because the Hajnal line was stable for centuries. At that rate an edge state moves
  about a fifth of the way to its neighbours in 50 years.
- **The interior of a bloc doesn't move:** its neighbours share its value.
- **Unverified:** whether `every_neighbouring_state` crosses water (Britain and France, Denmark and Sweden, Japan and
  Korea). A one-line probe settles it. If it doesn't, islands spread only through conditions.

### 4.5 Existing lines they collide with

- **`inh_primogeniture_rural`** (`common/static_modifiers/te_inheritance_modifiers.txt`) gives
  `state_birth_rate_mult` +0.1 × the agrarian share under Primogeniture: "large families".
  - In births per woman, impartible inheritance points the other way: the heir's large family is outweighed by the
    siblings who marry late or never.
  - Once the census sets births (phase 2), the two would contradict on Britain's and Japan's farms.
  - Recommended: drop the +0.1 birth line and keep its migration line (§7, call 4). Section 13 already proposes the
    same for Forced Heirship's −0.15 and Family Limitation.
- **Family Limitation (`te_demog_family_limitation`)** acts through the means, toward a desired size; the two
  practices act outside them (§2.1).
  - France has Family Limitation and Late Marriage, as history had (§1.1), and the fit needs both: France reads 3.7
    against history's 3.6 only with the two together.
  - Birth Spacing is not Family Limitation under another name. Family Limitation stops births at a size the couple
    wants, and does nothing where `desired` is near natural fertility. China's is 0.93 at literacy 0.13, so +0.6 of
    means would cut its births by about 4%. Birth Spacing cuts births whatever size is wanted.

## 5. Phase placement and calibration

### 5.1 Step 2: the harness first

Both terms go into the Python twin and the harness before any script, as step 2 of the calibration plan. The
harness needs:

1. **The model.**
   - `Inputs.late_marriage` and `Inputs.birth_spacing` (the shares), the two terms in `fertility()`, and their lines in
     the returned terms.
   - In `demographics_params.py`: `LATE_MARRIAGE_CUT`, `BIRTH_SPACING_CUT`, the two start tables (by strategic region
     and by state region), the drifts' constants, and the wealth curve's ends scaled by s.
2. **The save reader.**
   - `demographics_save_inputs` reads each state's `region` (one more field in `SECTIONS["states"]`; saves hold
     `region="STATE_X"`).
   - It maps state regions to strategic regions from the base game's `common/strategic_regions/` (the mod replaces
     only two North American ones).
   - Once the census stores the shares, the reader takes the state's variables instead (`read_variables`).
3. **`history`:**
   - both share columns;
   - a filter that keeps a country's incorporated states, so colonies stay out of a country's figure (in the gate
     game half of Denmark's 1887 people live in West Africa and South India);
   - the error over the anchor countries;
   - the world line.
4. **`fertility`:** each scenario gets the shares the drift gives it.

   | Scenario | Late Marriage | Birth Spacing | Reads, at the proposal | Band |
   |---|---|---|---|---|
   | Britain 1836 | 1.0 | 0 | 4.48 | 4.5–5.8 |
   | France 1836 | 1.0 | 0 | 3.94 | 3.4–5.0 |
   | Britain 1900 | 0.75 | 0 | 3.43 | 3.2–4.0 |
   | West 1950 | 0.5 | 0 | 2.49 | 2.3–3.5 |
   | West 1990 | 0.45 | 0 | 1.58 | 1.4–2.0 |
   | India 1975 | 0 | 0.2–0.38, by how far its means have eroded it | 5.35–5.72 | 4.7–5.8 |
   | The 1836 agrarian reference | 0.5 | 0 | 5.93 | 4.8–6.2 |

   Britain 1836's band was set before the terms, and is re-centred on history's 4.8–5.0.
5. **A drift replay:** step both shares through the gate run's six saves (1837–1887, ten years apart) with each
   save's conditions. It checks that the West and East Asia hold and the Hajnal line doesn't wander.
6. **A joint refit,** because step 1's and stage 2's numbers were fitted without the terms. It refits:
   - s and the two cuts;
   - the stage-2 era-3 means pair (vulcanization, feminism), so Britain 1900 and 1887 come back up;
   - step 1's poverty term and base infection, against life expectancy and growth as well as children per woman
     (§2.4). If it raises China's life expectancy, China's Birth Spacing can rise toward history's 5.5.

### 5.2 The gate

On the gate saves (1837, 1887) and the scenarios:
- **every anchor country within ±0.5 children per woman**, except those named in the results doc with a reason:
  marital fertility (the Low Countries), colonies (until the filter), and the flat Gapminder guesses (China, Persia,
  Turkey, Mexico, Peru), which carry half weight;
- **the error over the anchor countries 0.5 or less** (today 0.89);
- **world children per woman** within ±0.15 of today's (5.96 / 5.74);
- **world growth** within ±0.1% a year of step 1's (+1.08 / +0.98), and China's within ±0.1% of +0.32% in 1887;
- **life expectancy and growth**, after the joint refit:
  - Britain, Sweden and Denmark within 3 years of history's life expectancy (41 in 1837);
  - no anchor country of 20M people or more shrinking (Japan reads −0.15% a year in 1887 before the refit);
  - Persia's and Mexico's growth within 0.5% a year of history's;
- **every `fertility` and `medicine` scenario in band;**
- **the drift replay:** the West's Late Marriage at 0.8 or more and East Asia's Birth Spacing within 0.1 of its start
  through 1887, and no state's shares moving more than 0.2 by 1887 except through its own conditions.

The plan's phase 2 gate (a fast-mode run, world population 1836–1900 within ×1.3–×1.7, no large country losing
people for ten years) then tests it in game. Britain, Belgium and Japan are the countries to watch.

### 5.3 Script and panel

- **Phase 2, with the births:**
  - both shares as state variables;
  - their seeds from the generated tables;
  - the target drifts (§4.2, §4.3);
  - the two terms in the census's fertility, with their hover lines.

  The drifts belong in phase 2. Without them the West would keep a full Late Marriage share into the 20th century,
  and the census would set its births too low after 1930.
- **Phase 3:**
  - the neighbour spread, built with Family Limitation's general practice and Cultural Hegemony's fertility drift, the
    same spreading machinery (§13);
  - the blended age schedule (§2.5);
  - the later lever (§6).
- **The panel** shows both terms in the fertility hover, and each practice's people-weighted share on the overview.
  - Late Marriage, now strict, can show a real unit: women's mean age at first marriage ≈ 19 + 7 × the share (26 at
    1, 19 at 0).
  - Birth Spacing shows its share. A real unit (the birth interval) would need an anchor the spec doesn't have.
- **Cost:** two variables and a few dozen arithmetic steps a state a year; the neighbour walk in phase 3.

## 6. Later levers: a minimum marriage age

- **The 20th-century lever** is a minimum marriage age: India's 1929, 1949 and 1978 Acts, China's 1950 and 1980
  Marriage Laws, *wan, xi, shao* (§1.5).
- **A new law won't do.** A country holds one law per group, so a new law inside an existing group would displace
  that group's other laws.

The candidates, in existing groups:

| Carrier | Group | Fit |
|---|---|---|
| `law_compulsory_primary_school` | `lawgroup_childrens_rights` | schooling keeps girls unmarried; India's Act was framed as protecting children |
| `law_womens_suffrage`, `law_protected_class` | `lawgroup_rights_of_women` | marriage-age reforms came with women's legal reforms |
| `law_state_sponsored_family_planning`, `law_population_control_measures` | `lawgroup_family_reproductive_policy` | China's 1980 law came with its birth limits |
| The "Later, Longer, Fewer" measure (parent spec §8.1; not built) | Family Planning, Population Control | *wan* is "later marriage". Its "longer" (spacing) came from modern methods, so it belongs to the means, not to Birth Spacing |

- **Recommended:** a registered modifier type that raises Late Marriage's target, `state_late_marriage_target_add`,
  carried by those laws' `modifier` blocks.
  - This is the modifier-types rule (`2026-10-09-demographics-modifier-types-design.md`): the law's tooltip shows the
    line, and the census reads it with `modifier:`.
  - Population Control Measures and the measure carry the largest lines.
- **Rejected:**
  - an amendment ("Minimum Marriage Age" on those laws), since it needs a scripted way in (CLAUDE.md, amendments);
  - a new law, which would displace its group's others.
- **The other way:** a state that makes early marriage cheap, such as housing allotted to married couples, lowered
  the age in the socialist east (§1.5, *unverified*). The modifier type takes a negative line if the owner wants one.
- **No lever for Birth Spacing.** It is custom that only erodes, and no state set out to restore it.

## 7. Owner calls

Decided (owner, 2026-10-10): two practices, combined as a product (§2.1).

1. **The names:** "Late Marriage" and "Birth Spacing". "Marital Restraint" and "Customary Restraint" are the
   alternatives for the second; "Birth Spacing" is plain, describes what it does, and doesn't echo Family
   Limitation. Recommended as proposed.
2. **Birth Spacing's start set** (§3.3): Japan 1.0; China, Manchuria and Korea 0.38; India 0.38.
   - India rests on its census-era anchor, with the mechanism unverified. At 0 instead it reads about a child high
     and grows +0.5% a year faster.
   - Korea has no anchor.
   - Recommended as proposed, with both flagged.
3. **Japan in Birth Spacing at 1.0 and Late Marriage at 0** (§1.3). Starting it in both changes nothing measurable,
   and the evidence is restraint within marriage. Recommended.
4. **The size:** wealth curve ×1.15, Late Marriage cut 0.30, Birth Spacing cut 0.34 (§2.3). The high-fertility
   group reaches about 7 at an error of 0.49 (today 0.89).
   - The harness refits the values jointly (§5.1).
   - Drop `inh_primogeniture_rural`'s +10% birth line, which contradicts Late Marriage (§4.5).
   - Recommended.
5. **Birth Spacing's erosion:** contraception plus health-care access as a stand-in for modernisation, which gives
   the Meiji rise (§4.3). The alternative is contraception only. Recommended: both, with the access weight fitted
   against Japan 1880–1910.
6. **Late Marriage's drivers:** impartible inheritance and women's paid work raise it, contraception erodes it.
   Literacy, urbanisation, SoL, wage labour and servants are left out (§4.1). Recommended as listed.
7. **Per state, for both practices and for Family Limitation when phase 3 generalises it,** on one machinery with
   one neighbour spread (§3.1). Recommended.
8. **Step 2 refits step 1's mortality jointly** (§2.4): births that match history leave the West growing too slowly,
   Japan shrinking, and the Middle East and Latin America too fast. Recommended: one joint fit, with the gate in
   §5.2.
9. **The later lever:** lines of `state_late_marriage_target_add` on existing laws and the "Later, Longer, Fewer"
   measure, in phase 3 (§6). Recommended over an amendment or a new law.
