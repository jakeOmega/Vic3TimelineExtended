# Demographics phase 3: Family Limitation as a general practice, the fit (2026-10-12)

The harness half of phase 3's Family Limitation (parent spec `docs/superpowers/specs/2026-10-08-demographics-design.md`
§13; owner, 2026-10-12: build it as proposed, a national practice; one pass, "close enough", the owner reviews the
results). The check the brief set: **France's, Belgium's and Switzerland's fertility decline timing** against
Gapminder. Also here: the neighbour spread of Late Marriage and Birth Spacing (the late-marriage spec §4.4) against its
§5.2 replay items, the fertility scenarios (its §5.1 bands), #904's regional growth, and Cultural Hegemony's drift on
two scenarios.

## The data

- **The saves:** the overnight normal-speed Full run of 2026-10-12 (`/mnt/d/vic3te-data/vic3te-demog-overnight-2026-10-12/saves/`,
  main 4002821a; its notes in `session-notes-2026-10-12/REPORT.md`), every fifth year from 1837 to 1902 and 1904 (15
  saves). The replay steps every year between two saves at the earlier save's conditions.
- **The anchors:** `/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv` (Gapminder's children per woman), each
  save year's nearest anchor within 5 years.
- **#904's state-years** for the run: `session-notes-2026-10-12/rows.json` (53,757 rows; the projection reads the steps
  of 1837–1900).
- **The neighbours:** `scripts/analysis/demographics_state_adjacency.json` (`demographics_adjacency.py --refresh`: 624
  state regions with land neighbours, from the game's `provinces.png`; 26 straits kept apart). A country's neighbours are
  the states another country owns in a region next to one of its own, or in one of its own, weighted by their people.
- **The model:** each state's own inputs from the save (`demographics_practices.practice_states`), the practices at the
  save's own shares. "Today" is the build before phase 3: France's history modifier at +0.6 in the means, and Forced
  Heirship's −15% × the farm share on top (the census applies it at its rate under Full). "With" is the practice: each
  country's line in its states' means, and the cut folded in. Births and deaths elsewhere are as the run had them.

Commands:

```
demographics_harness.py fl-replay SAVES --anchors A          # the tables below
demographics_harness.py practices-replay SAVES               # the spread (--no-spread: phase 2's replay)
demographics_harness.py fertility                            # the scenarios
demographics_harness.py ch-drift                             # Cultural Hegemony's drift
```

## The one pass

A grid of 36 points over the neighbour rate (0, 0.01, 0.02, 0.04 a year), the Forced Heirship weight (0.6, 0.8, 1.0)
and the literacy weight (0, 0.3, 0.6, from literacy 0.6), scored by the error in children per woman over the three
check countries:

- **Forced Heirship 1.0** is best at every point (France 0.65 against 0.70 at 0.6–0.8): France's target is then its
  farm share, 0.73 in 1837, so its share rises from history's 0.6 instead of holding.
- **The literacy term only hurts** (every weight above 0 raises the error): the game's literacy rises fast in the
  West (Belgium 0.42 in 1837, 0.73 by 1852; Denmark 0.74, Prussia 0.64) while France's stays at 0.25–0.33 all century,
  so literacy is no clock for the decline here. The brief names it, so it stays, from literacy **0.8** (full at 1.0) at
  weight 0.3: nearly nothing before 1900 in these saves (Belgium's target reaches 0.04 in 1902), a small part of a
  literate 20th century, by which time modern contraception has taken most of the line.
- **The neighbour rate 0.02** (error 0.625; 0.04 gives the same 0.625 by trading Belgium for Switzerland). Chosen over
  0.04 for its smaller reach into the rest of Europe (controls 0.474 against 0.487).

Decided values (`demographics_params.py`, phase 3 block): rate to target 0.025 (Late Marriage's), neighbour rate 0.02,
Forced Heirship 1.0, literacy 0.3 from 0.8 to 1.0 × the church law (State Religion 0.5, Freedom of Conscience 1, Total
Separation and State Atheism 1.5), no line below 0.02, the line eroded as Late Marriage's start is.

## The check: decline timing

Error over the three, every save: **0.651 today, 0.625 with the practice.** Per country: France 0.65 / 0.65,
Belgium 0.28 / 0.46, Switzerland 0.88 / 0.73.

**France**

| Year | Share | Line | Target | Neighbours | Today | With | Gapminder |
|---|---|---|---|---|---|---|---|
| 1837 | 0.60 | 0.60 | 0.73 | 0.00 | 3.48 | 3.92 | 3.60 |
| 1842 | 0.62 | 0.62 | 0.74 | 0.01 | 3.52 | 3.95 | 3.54 |
| 1847 | 0.63 | 0.63 | 0.74 | 0.01 | 3.49 | 3.89 | 3.51 |
| 1852 | 0.64 | 0.64 | 0.74 | 0.02 | 3.51 | 3.90 | 3.42 |
| 1857 | 0.65 | 0.65 | 0.74 | 0.03 | 3.52 | 3.90 | 3.36 |
| 1862 | 0.66 | 0.66 | 0.00 | 0.03 | 3.92 | 3.85 | 3.46 |
| 1867 | 0.66 | 0.66 | 0.00 | 0.03 | 4.01 | 3.94 | 3.55 |
| 1872 | 0.66 | 0.66 | 0.00 | 0.03 | 4.05 | 3.99 | 3.59 |
| 1877 | 0.66 | 0.66 | 0.00 | 0.03 | 4.02 | 3.95 | 3.49 |
| 1882 | 0.66 | 0.66 | 0.00 | 0.04 | 4.05 | 3.98 | 3.40 |
| 1887 | 0.66 | 0.66 | 0.00 | 0.05 | 4.04 | 3.97 | 3.22 |
| 1892 | 0.66 | 0.66 | 0.00 | 0.05 | 4.09 | 4.03 | 2.96 |
| 1897 | 0.66 | 0.66 | 0.00 | 0.06 | 3.86 | 3.81 | 2.92 |
| 1902 | 0.66 | 0.65 | 0.00 | 0.06 | 3.81 | 3.76 | 2.85 |
| 1904 | 0.66 | 0.66 | 0.00 | 0.06 | 3.85 | 3.80 | 2.75 |

**Belgium**

| Year | Share | Line | Target | Neighbours | Today | With | Gapminder |
|---|---|---|---|---|---|---|---|
| 1837 | 0.00 | 0.00 | 0.00 | 0.26 | 4.87 | 4.87 | 4.98 |
| 1842 | 0.02 | 0.02 | 0.00 | 0.26 | 4.84 | 4.79 | 4.88 |
| 1847 | 0.05 | 0.05 | 0.00 | 0.27 | 4.62 | 4.52 | 4.58 |
| 1852 | 0.07 | 0.07 | 0.00 | 0.26 | 4.52 | 4.37 | 4.25 |
| 1857 | 0.09 | 0.09 | 0.00 | 0.26 | 4.48 | 4.29 | 4.44 |
| 1862 | 0.11 | 0.11 | 0.00 | 0.27 | 4.48 | 4.24 | 4.61 |
| 1867 | 0.12 | 0.12 | 0.00 | 0.27 | 4.38 | 4.10 | 4.73 |
| 1872 | 0.14 | 0.14 | 0.00 | 0.29 | 4.42 | 4.10 | 4.85 |
| 1877 | 0.15 | 0.11 | 0.00 | 0.30 | 4.20 | 3.93 | 4.80 |
| 1882 | 0.17 | 0.12 | 0.00 | 0.30 | 4.12 | 3.83 | 4.64 |
| 1887 | 0.18 | 0.14 | 0.00 | 0.31 | 4.16 | 3.84 | 4.36 |
| 1892 | 0.19 | 0.15 | 0.00 | 0.31 | 4.14 | 3.78 | 4.20 |
| 1897 | 0.20 | 0.08 | 0.00 | 0.32 | 3.88 | 3.69 | 4.02 |
| 1902 | 0.22 | 0.07 | 0.04 | 0.39 | 3.89 | 3.72 | 3.73 |
| 1904 | 0.22 | 0.07 | 0.02 | 0.38 | 3.86 | 3.69 | 3.63 |

**Switzerland**

| Year | Share | Line | Target | Neighbours | Today | With | Gapminder |
|---|---|---|---|---|---|---|---|
| 1837 | 0.00 | 0.00 | 0.00 | 0.24 | 5.04 | 5.04 | 4.14 |
| 1842 | 0.02 | 0.02 | 0.00 | 0.25 | 4.93 | 4.90 | 4.14 |
| 1847 | 0.04 | 0.04 | 0.00 | 0.25 | 4.87 | 4.80 | 4.14 |
| 1852 | 0.06 | 0.06 | 0.00 | 0.25 | 4.88 | 4.78 | 3.89 |
| 1857 | 0.08 | 0.08 | 0.00 | 0.25 | 4.89 | 4.77 | 3.85 |
| 1862 | 0.10 | 0.10 | 0.00 | 0.25 | 4.89 | 4.75 | 4.18 |
| 1867 | 0.11 | 0.11 | 0.00 | 0.26 | 4.92 | 4.76 | 4.16 |
| 1872 | 0.13 | 0.13 | 0.00 | 0.23 | 4.94 | 4.76 | 3.99 |
| 1877 | 0.14 | 0.14 | 0.00 | 0.26 | 4.87 | 4.66 | 4.29 |
| 1882 | 0.15 | 0.14 | 0.00 | 0.26 | 4.74 | 4.53 | 3.87 |
| 1887 | 0.16 | 0.15 | 0.00 | 0.27 | 4.75 | 4.53 | 3.74 |
| 1892 | 0.17 | 0.16 | 0.00 | 0.26 | 4.76 | 4.52 | 3.71 |
| 1897 | 0.18 | 0.10 | 0.00 | 0.27 | 4.72 | 4.55 | 3.79 |
| 1902 | 0.19 | 0.10 | 0.00 | 0.28 | 4.58 | 4.40 | 3.82 |
| 1904 | 0.19 | 0.10 | 0.00 | 0.28 | 4.59 | 4.40 | 3.66 |

| Country | 1837 today / with / history | 1867 | 1887 | 1904 | share 1904 |
|---|---|---|---|---|---|
| United Kingdom | 4.70 / 4.70 / 4.79 | 4.34 / 4.34 / 4.94 | 3.98 / 3.98 / 4.24 | 3.89 / 3.89 / 3.35 | 0.01 |
| Netherlands | 4.80 / 4.80 / 5.11 | 4.19 / 4.16 / 5.04 | 4.08 / 3.87 / 5.16 | 3.66 / 3.48 / 4.38 | 0.32 |
| Germany | 4.65 / 4.65 / 4.90 | 4.44 / 4.44 / 5.11 | 4.47 / 4.47 / 5.23 | 4.16 / 4.16 / 4.68 | 0.04 |
| Spain | 5.27 / 5.27 / 5.13 | 5.19 / 5.03 / 5.09 | 4.95 / 4.63 / 4.78 | 4.60 / 4.21 / 4.67 | 0.19 |
| Italy | 5.17 / 5.17 / 5.47 | 5.17 / 4.97 / 4.92 | 5.03 / 4.88 / 5.03 | 4.97 / 4.70 / 4.44 | 0.14 |
| Denmark | 4.53 / 4.53 / 4.04 | 4.51 / 4.51 / 4.09 | 4.60 / 4.60 / 4.28 | 4.15 / 4.45 / 3.97 | 0.21 |
| Sweden | 4.54 / 4.54 / 4.37 | 4.41 / 4.41 / 4.40 | 4.33 / 4.33 / 4.36 | 4.05 / 4.05 / 3.77 | 0.00 |
| Austria | 5.07 / 5.07 / 5.10 | 4.83 / 4.83 / 4.81 | 4.84 / 4.84 / 4.49 | 4.89 / 4.89 / 4.17 | 0.02 |


Controls' error, today against with: 0.452 / 0.474 (Britain 0.44 / 0.44, the Netherlands 0.80 / 0.88, Germany 0.64 /
0.65, Spain 0.24 / 0.21, Italy 0.31 / 0.28, Denmark 0.28 / 0.36, Sweden 0.22 / 0.22, Austria 0.34 / 0.34). Italy's share
restarts at 1872 because the harness keys countries by tag and Sardinia became Italy (in game the formed country keeps
its variables).

**The verdict, country by country:**

- **France: the head start holds; the late decline doesn't come.** Gapminder falls from 3.6 to 2.75 after 1880. The
  model stays at 3.9–4.0 and reaches 3.8 by 1904, with the practice or without. The game's France keeps its 1836
  literacy (0.25–0.33) and cities all century, so its desired family size stays high (0.79) and the means, which close
  only the gap to it, have nothing more to close: France's means already sit near their cap at a share of 0.66. In
  this run the AI dropped Forced Heirship in 1862, so France's target fell to 0 and the share held at 0.66 (it rises
  only). **The fold raises France's 1837 figure from 3.48 to 3.92** (Gapminder 3.60) while it holds Forced Heirship:
  the old cut acted on births directly, and the means can't carry all of it (they close at most a fifth of the
  births in 1836 France). Within the France 1836 scenario's band (3.4–5.0).
- **Belgium: matches by 1902, too early before.** Gapminder is flat at 4.6–4.85 until 1880 and falls to 3.6 by 1904.
  The model falls from 1842 already, today's as much as with the practice (literacy 0.42 → 0.79 by 1867, cities, then
  Vulcanization in 1877); the practice reaches a share of 0.22 by 1904 from France's border and steepens that early fall
  by 0.1–0.35 children. Its line erodes with contraception from 1877 (0.15 → 0.07 by 1897).
- **Switzerland: the right shape, too high.** Gapminder falls from 4.1 to 3.7, faster after 1880; the model from 5.0 to
  4.6 today, 4.4 with the practice (a share of 0.19 by 1904). The practice closes about a fifth of the gap.
- **The spread's reach** by 1904: Spain 0.19, Belgium 0.22, Switzerland 0.19, Italy 0.14 (0.15 as Sardinia by 1867),
  Germany 0.04, Britain 0.01 (no land border with France), Sweden and Austria about 0. Spain and Italy move toward
  Gapminder; the Netherlands and Denmark, which took Forced Heirship in this run, move away (Denmark's 1892–1904 figure
  rises: the cut it gained in 1892 is folded into a practice that takes a generation to rise).

## The practices' spread (late-marriage spec §5.2 items)

`practices-replay` on the same saves, land neighbours only:

- The West's Late Marriage: 0.999 (1837), 0.997 (1857), 0.987 (1887), 0.899 (1904): at least 0.8 through 1887. **Pass.**
- East Asia's Birth Spacing: Japan 1.000, China, Manchuria and Korea 0.060 at every save: within 0.1 of the start.
  **Pass.**
- The spread's own moves by 1887 (the replay with it less the one without): at most 0.087 (West Karelia's Late
  Marriage, 0.99 → 0.91), then Tallinn 0.08, Kola +0.07, Courland and Riga 0.06: all at the Hajnal line's edges, all
  under 0.2. **Pass.** With straits: at most 0.13 (Birth Spacing reaching the Ryukyu Islands and Sakhalin from Japan).

## The fertility scenarios (late-marriage spec §5.1 bands)

Unchanged, every one in band: Family Limitation's start line is today's +0.6 on the France 1836 row (4.28, 3.4–5.0),
and the other rows hold no practice. 1836 agrarian 5.58, Britain 1836 4.86, Britain 1900 3.47, West 1950 2.38, West
1990 1.51, India 1975 5.17, East Asia 1990 1.92, Latin America 1970 4.03 (the women's-rights rows likewise).

## #904's regional growth (peacetime births less deaths, per 1,000 a year, 1837–1900)

The practice moves births only. W/N/C/S Europe: **+10.99 → +10.68** (history +8 to +10, widened to +10.5); Africa
+9.05 → +8.97 (France's colonies take its line, as they took history's modifier); South America +11.87 → +11.84;
Oceania +6.42 → +6.32; the world **+8.53 → +8.49**. Every other region unchanged.

## Cultural Hegemony's drift (`ch-drift`)

At its target (no game in these saves had the Cultural Hegemony journal entry long enough to move it):

| Scenario | Exposure | Hegemon's desired | Own | Factor | Children per woman |
|---|---|---|---|---|---|
| Latin America 1970, a 25-point lead | 0.25 | 0.45 | 0.53 | 0.981 | 4.03 → 4.00 |
| India 1975, a 30-point lead | 0.30 | 0.45 | 0.71 | 0.945 | 5.17 → 5.07 |
| West 1990, a rival 10 points behind | 0.10 | 0.45 | 0.35 | 1.015 | 1.59 → 1.60 |

Small, as the spec asks: La Ferrara, Chong and Duryea (2012) put the novelas' effect at about 5% fewer births where
they reached.

## What's left open

- France's late decline needs France's own conditions to move (the game's France doesn't modernize its literacy), or a
  practice that acts outside the means; neither is this pass's.
- Belgium's early fall is today's model's (literacy and cities), not the practice's; the practice steepens it.
- Whether `every_neighbouring_state` crosses straits, and what it returns from country scope: the self-checks
  (`docs/testing/demographics-playtest.md`).
