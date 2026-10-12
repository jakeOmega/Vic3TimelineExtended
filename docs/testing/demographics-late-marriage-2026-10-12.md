# Demographics: Late Marriage and Birth Spacing, the fit (2026-10-12)

The harness half of the late-marriage plan (`docs/superpowers/plans/2026-10-11-demographics-late-marriage.md`, Task 6;
spec `docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md`). It fits the wealth curve's raise, the
two cuts, the two held Birth Spacing shares, step 1's poverty term and base infection, and the era-3 means pair on the
normal-speed run's saves, and judges them by the owner's regional growth gate (plan D12, D13).

**Status: Stop A. No point passes the gate.** No raise from 1.00 to 1.20 has a mortality point that puts every region
inside its band. Following the plan's fallback, the branch applies the smallest raise whose best point fails the
fewest regional items: **no raise (s = 1.00)**, Late Marriage's cut **0.10**, Birth Spacing's **0.20**, India's and
East Asia's held shares **0**, and step 1's poverty term refitted to **×2.25 at SoL 5, ×1 from SoL 8** (was ×1.75,
×1 from SoL 9). Four regional items still fail: India, the USA and Canada, Southeast Asia, and Japan as a country
shrinking. Britain's life expectancy also stays 3.7 years short of 41, as it is today. The owner decides at Stop A.
No script reads the practices yet (Task 8), so the only change a game sees is the poverty term, wherever the census
runs: its figures under Display only, and its births and deaths under Full. Don't deploy this branch before Task 8.

## The build and the data

- **The build:** branch `feat/demog-late-marriage`, the plan branch with `main` at 4002821a merged in. The values were
  applied in the commit that adds this file.
- **The saves:** the normal-speed run's yearly autosaves, `/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11/saves/`,
  made by ec304526. The fit reads the eight of 1837, 1847, 1857, 1867, 1877, 1887, 1897 and 1901; the children per
  woman error reads 1837 and 1887 (plan D8).
  - The save reader is ec304526's but for #904's read buffer (checked: the two files differ only there).
  - The census model is ec304526's on these saves: they hold none of #916's stored inputs (`te_dg_in_*`), so medicine
    sits at its targets and turmoil at 0, as ec304526's census had them. The carriers gained only #916's
    `state_medical_diffusion_add` lines since, which do nothing with medicine at its targets.
  - `predict` and `fidelity` were not run (they need an ec304526 worktree).
- **The anchors:** `/mnt/d/vic3te-data/history-anchors-2026-10-10/anchors.csv` (Gapminder's children per woman,
  Clio Infra's life expectancy).
- **#904's state-years:** `session-notes-2026-10-11/regional-rates/analyze.py data --json` with its defaults
  (devastation under 5, radicals under a quarter, severe starvation under 10%, no war or famine at either save). The
  file equals the archived `rows.json` row for row (53,697 rows). The projection reads the steps of 1837–1900, the
  span of #904's table: the rows also hold 1901's steps (from the 1902 save), which the table leaves out
  (`demographics_practices.peacetime_span`).
- **The strategic regions:** `scripts/analysis/demographics_strategic_regions.json` (36 land regions, 675 state
  regions; the same grouping as #904's `analyze.py`, 0 of 675 differ).

## Today

No practices, the 6.0 curve, the poverty term at ×1.75 below SoL 9 (`practices-fit … --s 1.0 --lm 0 --bs 0 --at
1,0,0,0,0`). Children per woman over the anchor countries: error 0.85. The world's (countries of 1M or more): 5.74 in
1837, 5.52 in 1887. Western life expectancy in 1837: Britain 37.3, Sweden 39.7, Denmark 40.1 (history 41). Every
fertility and medicine scenario is in band.

Peacetime births less deaths, per 1,000 a year, 1837–1900. The measured column reproduces #904's to 0.1:

| Region | Today | History, normal years |
|---|---|---|
| China | +6.5 | +3 to +6 |
| India | +11.7 | +6 to +9 |
| Western, northern, central, southern Europe | +11.1 | +8 to +10 |
| Africa | +8.8 | +3 to +8 |
| USA, Canada | +13.6 | +17 to +21 |
| Eastern Europe, Balkans | +11.4 | +8 to +12 |
| Japan, Korea, Manchuria | +7.8 | +2 to +6 |
| Russia, Siberia | +10.8 | +10 to +13 |
| Middle East, Central Asia | +8.8 | +4 to +8 |
| South America | +11.5 | +12 to +16 |
| Southeast Asia | +8.7 | +9 to +13 |
| Mexico, Central America | +11.6 | +10 to +13 |
| Oceania | +10.6 | – |
| **World** | **+8.8** | the gate: +7.75 or less |

Ten items fail today: nine regions and the world. Eastern Europe, Russia and Mexico pass.

## The replay

`practices-replay` over the eight saves, at the start values and again at the applied ones. The shares are the same
both times; only the held starts differ (0.37 at the start values, 0 applied). No gate line prints.

| Save | The West's Late Marriage | Japan's Birth Spacing | China, Manchuria, Korea (start values / applied) |
|---|---|---|---|
| 1837–1877 | 1.00 | 1.00 | 0.37 / 0 |
| 1887 | 0.99 | 1.00 | 0.37 / 0 |
| 1897 | 0.96 | 1.00 | 0.37 / 0 |
| 1901 | 0.93 | 0.99 | 0.37 / 0 |

The largest moves by 1901 are each state's own conditions (phase 2 has no spread):
- Istria, 0.50 → 0.16 (target 0.26);
- the German and Bohemian industrial states, 1.00 → 0.82–0.87, toward targets of 0.42–0.58: era-3 contraception
  reached them in the 1880s.

The West holds 0.8 or more through 1887, and East Asia holds its start.

## The fit: the cuts at each raise

For each raise, the cuts with the least error in children per woman over the anchor countries (1837 and 1887,
incorporated states, the flat guesses at half weight). Columns: India's held share (the cancel share); East Asia's
share at today's mortality (D13); China's children per woman; the early-marrying group (Persia, Turkey, Russia,
Mexico, Argentina) in 1837; and the gate items failing at today's mortality.

| Raise s | Cuts (Late Marriage, Birth Spacing) | Error | India | East Asia | China 1837 / 1887 | High group | Failing |
|---|---|---|---|---|---|---|---|
| 1.00 | 0.10, 0.20 | 0.71 | 0.00 | 0.06 | 5.82 / 5.70 | 5.51–5.88 | 8 |
| 1.05 | 0.15, 0.25 | 0.60 | 0.19 | 0.23 | 5.83 / 5.70 | 5.79–6.17 | 8 |
| 1.10 | 0.20, 0.30 | 0.53 | 0.30 | 0.34 | 5.82 / 5.69 | 6.06–6.47 | 8 |
| 1.15 | 0.25, 0.30 | 0.50 | 0.43 | 0.47 | 5.82 / 5.70 | 6.34–6.76 | 10 |
| 1.20 | 0.30, 0.35 | 0.52 | 0.48 | 0.50 | 5.83 / 5.71 | 6.61–7.05 | 12 |

The plan's grid (Late Marriage 0.20–0.40, Birth Spacing 0.25–0.45) put the best cuts for 1.00 and 1.05 on its floor.
Those two rows come from a second run with the grid extended down (0.05–0.25, 0.10–0.30). The 1.10 row is the same in
both runs. The spec's raise, 1.15, still gives the least error, but it fails ten items before any mortality refit.

## Mortality: no point passes

Each raise at its cuts, over the plan's 60 mortality points: the poverty term at SoL 5 (×1.50, 1.75, 2.00, 2.25), the
SoL from which it is ×1 (8, 9, 10), and base infection (×0.90 to ×1.30). East Asia's share is chosen at each point. The
fewest failing regional items at each raise:

| Raise s | Best point (floor, SoL, infection) | Failing regional items | Its other failures |
|---|---|---|---|
| **1.00** | **×2.25, 8, ×1.00** | **4:** India, USA and Canada, Southeast Asia, Japan shrinking | Britain's life expectancy 37.3 |
| 1.05 | ×2.25, 9, ×1.00 | 7: China, Europe, USA and Canada, Japan-Korea-Manchuria, South America, Southeast Asia, Japan shrinking | Britain 37.3 |
| 1.10 | ×2.25, 8, ×1.20 | 6: China, Europe, USA and Canada, Japan-Korea-Manchuria, Southeast Asia, Japan shrinking | life expectancy 33–36 in the West; 5 scenarios out of band |
| 1.15 | ×2.00, 9, ×1.20 | 7: the same, and China shrinking | the same |
| 1.20 | ×2.00, 9, ×1.20 | 8: China, Europe, Africa, Japan-Korea-Manchuria, Middle East, Mexico, China and Japan shrinking | the same; 6 scenarios out |

Every region reaches its band at some raise and point (the USA and Canada only with a raise), but none reaches
it with all the others:
- The knobs read standard of living alone, so they move two groups the same way.
  - One group has deaths too low for its SoL: India, Africa, the Middle East, and with any raise Russia, Mexico and
    Eastern Europe.
  - The other has deaths too high: Europe, Japan, the USA and Southeast Asia.
- A raise lifts births wherever neither practice holds, so every raise above 1.00 pushes the first group further out.
- Base infection ×0.90 brings Britain's life expectancy to 39.6, inside the 3-year rule. It also lifts India, Africa,
  the Middle East and Mexico out of their bands. At ×1.00 Britain reads 37.3 at every point.

The chosen point (the plan's fallback): the smallest raise with the fewest failures, 1.00. Its best point is
×2.25 / SoL 8 / ×1.00, and nothing ties with it. Re-running Step 4 at that point leaves the cuts at 0.10 and 0.20
(error 0.71).

## The chosen point against today's mortality

Both columns at s 1.00 and cuts 0.10 and 0.20; per 1,000 a year, to two decimals where the item is close:

| Region | Today's mortality (×1.75, SoL 9) | Chosen (×2.25, SoL 8) | History |
|---|---|---|---|
| China | +5.93 | +5.79 | +3 to +6 |
| India | +11.70 fail | +11.66 fail | +6 to +9 |
| Europe (W, N, C, S) | +7.99 fail (by 0.01) | +8.48 | +8 to +10 |
| Africa | +8.70 fail | +7.95 (inside by 0.05) | +3 to +8 |
| USA, Canada | +13.53 fail | +13.91 fail | +17 to +21 |
| Eastern Europe, Balkans | +10.67 | +10.88 | +8 to +12 |
| Japan, Korea, Manchuria | +3.01 | +2.01 (inside by 0.01) | +2 to +6 |
| Russia, Siberia | +10.63 | +11.33 | +10 to +13 |
| Middle East, Central Asia | +8.77 fail | +7.65 | +4 to +8 |
| South America | +11.49 fail | +12.10 | +12 to +16 |
| Southeast Asia | +8.56 fail | +6.69 fail | +9 to +13 |
| Mexico, Central America | +11.49 | +12.29 | +10 to +13 |
| Oceania | +10.59 | +10.66 | – |
| **World** | +7.83 fail (by 0.08) | **+7.67** | +7.75 or less |
| Countries of 20M+ shrinking | none | **Japan, −0.9** | none |

- Today's mortality fails six items outright and two by rounding (Europe and the world).
- The chosen point fails four. It passes Africa and the Japan group by hairs.
- It takes Japan's life expectancy from 27.7 to 23.4 in 1887 (history 37 in 1885). That puts Japan's steady growth at
  −1.0% a year, against history's +0.85%.

## Children per woman at the chosen point

Error 0.71 (today 0.85; the spec's gate was 0.5, which the owner's ruling no longer requires). Incorporated states;
"off" is more than 0.5 from Gapminder:

| Country | 1837 today | 1837 fitted | 1837 history | 1887 today | 1887 fitted | 1887 history |
|---|---|---|---|---|---|---|
| Argentina | 5.68 | 5.67 off | 6.80 | 5.48 | 5.46 off | 6.14 |
| Austria | 5.32 | 4.97 | 5.10 | – | – | – |
| Belgium | 5.43 | 4.88 | 4.98 | 4.36 | 3.93 | 4.36 |
| Brazil | 5.73 | 5.73 off | 6.26 | 5.19 | 5.18 off | 6.24 |
| Chile | 5.73 | 5.71 | 5.98 | 4.81 | 4.81 | 4.42 (dropped) |
| China | 5.89 | 5.88 | 5.50 (half) | 5.77 | 5.75 | 5.50 (half) |
| Denmark | 5.02 | 4.52 | 4.04 | 5.22 | 5.02 off | 4.28 |
| Egypt | 5.81 | 5.81 | 6.05 | 5.50 | 5.48 off | 6.03 |
| France | 5.13 | 4.63 off | 3.60 | 5.05 | 4.55 off | 3.22 |
| Germany | 5.14 | 4.65 | 4.90 | 4.41 | 3.98 off | 5.23 |
| India | 5.76 | 5.75 | 5.95 | 5.72 | 5.72 | 5.76 |
| Iran | 5.88 | 5.88 off | 7.08 (half) | 5.69 | 5.68 off | 7.08 (half) |
| Italy | 5.57 | 5.22 | 5.47 | 4.89 | 4.61 | 5.03 |
| Japan | 5.57 | 4.46 | 4.54 | 5.38 | 4.28 | 4.04 |
| Korea | 5.87 | 5.86 | – | – | – | – |
| Mexico | 5.79 | 5.77 off | 6.80 (half) | 5.62 | 5.59 off | 6.80 (half) |
| Netherlands | 5.35 | 4.81 | 5.11 | 5.42 | 5.09 | 5.16 |
| Portugal | 5.60 | 5.11 off | 4.50 | 5.54 | 5.12 off | 4.38 |
| Russia | 5.51 | 5.50 off | 7.00 | 5.37 | 5.33 off | 6.61 |
| Spain | 5.65 | 5.25 | 5.13 | 5.34 | 4.97 | 4.78 |
| Sweden | 5.04 | 4.54 | 4.37 | 4.82 | 4.34 | 4.36 |
| Turkey | 5.85 | 5.85 off | 6.92 (half) | 5.55 | 5.55 off | 6.92 (half) |
| United Kingdom | 5.21 | 4.69 | 4.79 | 4.52 | 4.08 | 4.24 |
| United States | 5.40 | 5.40 off | 6.24 | 5.39 | 5.38 off | 4.43 (dropped) |

What is left, and why:
- **The early-marrying world** (Argentina, Brazil, Iran, Mexico, Russia, Turkey, the USA in 1837) reads 0.5–1.5 low.
  That gap was the raise's job, and the gate allows no raise. The high group reads 5.50–5.88 against history's ~7. The
  owner's ruling accepts it: reported, not required.
- **France** reads about 1.0–1.3 high. Its pattern is Family Limitation (phase 3) on top of Late Marriage, and
  Late Marriage's cut of 0.10 takes off only a tenth.
- **Portugal** reads 0.6–0.7 high: north-western Iberia's 0.9 share at a 0.10 cut.
- **Denmark in 1887** reads 0.7 high. 70% of its incorporated people in that save live in Madras and the Niger
  Delta, at share 0, and the incorporated filter keeps incorporated colonies.
- **Germany in 1887** reads 1.3 low. The census's education, urban and means terms already bring it down, and Late
  Marriage compounds them (the spec's §2.3 note on Britain, here worse).
- **Egypt in 1887** reads 0.55 low, against a flat guess near 6.

## China, Manchuria and Korea (D13)

- East Asia's share at the chosen point is **0**, the cancel share at no raise. China's projected peacetime rate is
  +5.8 without any Birth Spacing, inside its +3 to +6 band, because the refitted poverty term raises its deaths.
- China's children per woman: **5.88 in 1837, 5.75 in 1887**, against history's 5.5 (a flat guess). That is above 5,
  so nothing is flagged.
- Korea: 5.86 in 1837, against a flat 6.0 guess the harness doesn't hold as an anchor.
- India's held share is 0 too: there is no raise to cancel.

**So Birth Spacing acts only in Japan** (1.0, cut 0.20: Japan 4.46 / 4.28 against history's 4.54 / 4.04). That
departs from the spec's call 2 (China, Manchuria, Korea and India at 0.38) and needs the owner's eye.

## The means pair

At the chosen point every vulcanization and feminism pair from 0.10 to 0.30 gives Britain the same 1887 figure (4.08):
era-3 contraception had not reached Britain by 1887 in this run. The pairs above 0.20 / 0.20 push West 1950, West 1990
with Women's Suffrage and Latin America 1970 out of band. So the pair stays at vulcanization 0.20 and feminism 0.15, and
`te_demog_tech_injections.txt` is unchanged.

## Scenarios and life expectancy at the chosen point

- **Fertility scenarios** (`fertility`, now judging each with its practices' shares): all 13 in band. Britain 1836
  4.86, France 1836 4.28, Britain 1900 3.47, West 1950 2.38, West 1990 1.51, India 1975 5.17, East Asia 1990 1.92,
  Latin America 1970 4.03 (its band starts at 4.0).
- **Medicine scenarios** (`medicine`): all in band. Every scenario sits at SoL 9 or above, where the poverty term
  doesn't reach.
- **Western life expectancy in 1837:** Britain 37.3, Sweden 39.8, Denmark 40.1. Britain fails the 3-year rule, as it
  does today.

## After: the applied build

`practices-replay` and `history --incorporated-only --shares` on the applied values match the chosen point's figures
to 0.01: for example China 5.88 / 5.75, Japan 4.46 / 4.28, Britain 4.69 / 4.08 and Russia 5.50 / 5.33. In the steady
model, 1887, the applied build puts:
- Japan at e0 23.4 and −1.03% a year;
- India at e0 32.0 (history 24 in 1891) and +1.02% a year;
- Britain at +0.81% (history +0.79%).

## The gate, item by item (the chosen point)

| Item | Figure | Verdict |
|---|---|---|
| Each region inside its band | 8 of 12 in; India, USA and Canada, Southeast Asia out | **fail** |
| The world at or below today's less 1 per 1,000 | +7.67 against +7.75 or less | pass |
| China +3 to +6 | +5.79 | pass |
| China's children per woman 5 or more (owner, 2026-10-12) | 5.88 / 5.75 | pass |
| No country of 20M+ with births below deaths | Japan −0.9 per 1,000 (54M) | **fail** |
| Britain, Sweden, Denmark within 3 years of 41 | 37.3, 39.8, 40.1 | **fail** (Britain) |
| Every fertility and medicine scenario in band | all 13 and all 7 | pass |

## What only calibration step 3 could fix

These regions fail on deaths that standard of living can't place. A geographic mortality term would separate them:

| Region | Its own children per woman | What it needs |
|---|---|---|
| India | 5.75 / 5.72, history 5.95 / 5.76: right | Deaths up by about a tenth at its SoL (life expectancy 32 against history's 24) |
| Japan (and the Japan group's edge) | 4.46 / 4.28, history 4.54 / 4.04: right | Deaths down by about a third (23 against 37) |
| Southeast Asia | no anchor | Deaths down, about 2.3–6.3 per 1,000 to reach its band |
| USA and Canada | 5.40, history 6.24 in 1837 | Deaths down (CDR 24.5 against 20–22), **and** births up |

**A finding for Stop A, not for step 3:** the USA's births. A raise of about 1.09 would close it. A raise is global,
though, and lifts every early-marrying region the same way, so it fails the gate elsewhere until step 3 separates their
deaths. Once step 3 exists the raise can be refitted with it: the spec's 1.15 gave the least children-per-woman error.

## The commands

```
D=/mnt/d/vic3te-data/vic3te-demog-p2-normal-2026-10-11
python3 $D/session-notes-2026-10-11/regional-rates/analyze.py $D/session-notes-2026-10-11/regional-rates/data --json ROWS
demographics_harness.py practices-fit SAVES --anchors A --peacetime ROWS --s 1.0 --lm 0 --bs 0 --at 1,0,0,0,0
demographics_harness.py practices-replay SAVES --out REPLAY
demographics_harness.py practices-fit SAVES --anchors A --peacetime ROWS --shares REPLAY \
  --s 1.00,1.05,1.10,1.15,1.20 --lm 0.20,0.25,0.30,0.35,0.40 --bs 0.25,0.30,0.35,0.40,0.45
demographics_harness.py practices-fit SAVES ... --s 1.00,1.05,1.10 --lm 0.05,0.10,0.15,0.20,0.25 --bs 0.10,0.15,0.20,0.25,0.30
demographics_harness.py practices-fit SAVES ... --s S --lm LM --bs BS --at S,LM,BS,HELD --mortality   # each raise
```

The re-run of the fit at the moved mortality point, and the two-decimal table above, patched the parameters in a
scratch wrapper (`DP.patch_params(POVERTY_INFECTION_AT_FLOOR=2.25, POVERTY_INFECTION_SOL=8)` around the same
functions). Each `practices-fit` reads the eight saves once, in about 4 minutes and 1.1 GB, and a 60-point mortality
grid takes about 8 minutes in all.
