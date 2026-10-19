# Demographics: Late Marriage and Birth Spacing, the fit (2026-10-12)

The harness half of the late-marriage plan (`docs/superpowers/archive/plans/2026-10-11-demographics-late-marriage.md`, Task 6;
spec `docs/superpowers/specs/2026-10-10-demographics-late-marriage-design.md`). It fits the wealth curve's raise, the
two cuts, the two held Birth Spacing shares, step 1's poverty term and base infection, and the era-3 means pair on the
normal-speed run's saves, and judges them by the owner's regional growth gate (plan D12, D13).

**Status: Stop A decided (owner, 2026-10-12): the fitted fertility with today's mortality.** No raise from 1.00 to
1.20 has a mortality point that puts every region inside its band (below, "Mortality: no point passes"). At Stop A the
owner took option 2: the fallback's fertility, with step 1's mortality left where it is. The branch holds:
- **no raise (s = 1.00)**: the wealth curve stays at 6.0 and 3.5;
- Late Marriage's cut **0.10**, Birth Spacing's **0.20**;
- India's held share **0**: with no raise there is nothing to cancel;
- China's, Korea's and Manchuria's share **0.06**: the smallest share that brings China's projected peacetime growth
  inside +3 to +6 at today's mortality (+5.9; +6.5 with none; plan D13);
- step 1's poverty term **unchanged** (×1.75 at SoL 5, ×1 from SoL 9). The fallback's ×2.25 refit was offered and not
  taken.

**The gate's verdict, as decided:**
- **Fail outright:** India, Africa, the USA and Canada, the Middle East, South America and Southeast Asia.
- **Fail by rounding:** Europe (+7.99 against at least +8) and the world (+7.83 against at most +7.75).
- **Pass:** China (+5.93), the Japan group (+3.01), Eastern Europe, Russia and Mexico.
- **No country of 20M or more shrinks.** Japan grows at +0.3 per 1,000.
- **Britain's life expectancy stays short** at 37.3, against 41 within 3 years, as it is today.

The failing regions are calibration step 3's: a geographic mortality term, which comes next.

**In game:** Task 9 took Plan A without the probe (owner, 2026-10-12): a once-a-game `TE_SELF_CHECK` line in
`debug.log` says whether the engine scales the type, and the in-game list is now `docs/testing/demographics-playtest.md`,
checked at the next play-test rather than before the merge.

Birth Spacing's health-care erosion reads the access medicine has reached (`te_dg_acc` above its base, which drifts
since #916), not the access modifier. That is a default chosen at the build and flagged for the owner. On these saves,
which predate #916's drift, the two are the same.

## The build and the data

- **The build:** branch `feat/demog-late-marriage`, the plan branch with `main` merged in (4002821a; later 0fd07218, whose
  demographics change, #921, touches only `fidelity`). The decided values are in `demographics_params.py` since the
  Stop A decision (2026-10-12).
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

`practices-replay` over the eight saves, at the start values and again at the decided ones. The shares are the same
both times; only East Asia's start differs (0.37 at the start values, 0.06 decided). India's is 0.37, then 0. No gate
line prints.

| Save | The West's Late Marriage | Japan's Birth Spacing | China, Manchuria, Korea (start values / decided) |
|---|---|---|---|
| 1837–1877 | 1.00 | 1.00 | 0.37 / 0.06 |
| 1887 | 0.99 | 1.00 | 0.37 / 0.06 |
| 1897 | 0.96 | 1.00 | 0.37 / 0.06 |
| 1901 | 0.93 | 0.99 | 0.37 / 0.06 |

The largest moves by 1901 are the German and Bohemian industrial states, 1.00 → 0.82–0.87, toward targets of 0.42–0.58:
era-3 contraception reached them in the 1880s.

**Corrected at Stop B (I1): Istria.** The first replay listed Istria, 0.50 → 0.16, as the largest move, put down to its
own conditions. Drift alone can't take a share below its target (0.26), so it couldn't be. The replay re-seeded Istria
from the table each time its state changed ID between the saves it samples, ten years apart.

**How the shares survive a change of owner (built at Stop B, 2026-10-12).** A change of owner moves the people to a
new state object, which carries none of the old one's variables.
- In this run Istria went through four objects in 20 years, piece by piece. Uruguay's whole state went to a
  revolution's winner in 1887.
- The shares survive in one of two ways:
  - **the siblings:** another piece of the state region still holds them at the new state's first census;
  - **the region's copy:** every step writes the shares on the state region (`te_dg_pr_<P>_r`, the last state to step),
    and the seed reads it when no sibling holds a share. That covers a whole region taken at once.
- Only a region with neither seeds at its start less what its conditions have eroded. In a new game, before any step
  has written a copy, that is the table.
- The replay mirrors this, carrying each region's copy across the sampled saves. Istria reads 0.54 in 1877 and 0.53 in
  1901, drifting toward its falling target.
- The fit doesn't move: the country table and the regional projection are identical to 0.01.

The census's ring and #916's medicine still re-seed on a whole-region transfer, as before. A state object with no
census seeds its ring at the stable structure of its own rates and its medicine at its targets. Task 12's in-game list
(item 5b) checks that the new state takes the region's copy.

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

The plan's fallback took the smallest raise with the fewest failures, 1.00. Its best point is ×2.25 / SoL 8 / ×1.00,
and nothing ties with it. Re-running Step 4 at that point leaves the cuts at 0.10 and 0.20 (error 0.71). That was
offered at Stop A as option 1. **The owner took option 2: the same fertility at today's mortality.**

## The decided point against the offered fallback

Both columns at s 1.00 and cuts 0.10 and 0.20, East Asia's share at each point's own pick; per 1,000 a year:

| Region | **Decided** (today's mortality: ×1.75, SoL 9; East Asia 0.06) | Offered fallback (×2.25, SoL 8; East Asia 0) | History |
|---|---|---|---|
| China | +5.93 | +5.79 | +3 to +6 |
| India | +11.70 **fail** | +11.66 fail | +6 to +9 |
| Europe (W, N, C, S) | +7.99 **fail** (by 0.01) | +8.48 | +8 to +10 |
| Africa | +8.70 **fail** | +7.95 (inside by 0.05) | +3 to +8 |
| USA, Canada | +13.53 **fail** | +13.91 fail | +17 to +21 |
| Eastern Europe, Balkans | +10.67 | +10.88 | +8 to +12 |
| Japan, Korea, Manchuria | +3.01 | +2.01 (inside by 0.01) | +2 to +6 |
| Russia, Siberia | +10.63 | +11.33 | +10 to +13 |
| Middle East, Central Asia | +8.77 **fail** | +7.65 | +4 to +8 |
| South America | +11.49 **fail** | +12.10 | +12 to +16 |
| Southeast Asia | +8.56 **fail** | +6.69 fail | +9 to +13 |
| Mexico, Central America | +11.49 | +12.29 | +10 to +13 |
| Oceania | +10.59 | +10.66 | – |
| **World** | +7.83 **fail** (by 0.08) | +7.67 | +7.75 or less |
| Countries of 20M+ shrinking | none (Japan +0.3) | Japan, −0.9 | none |

- The decided point fails six items outright and two by rounding (Europe and the world).
- The fallback failed four. It passed Africa and the Japan group by hairs, and took Japan's life expectancy from 27.7
  to 23.4 in 1887 (history 37 in 1885).
- `practices-fit --s 1.00 --lm 0.10 --bs 0.20 --at 1.00,0.10,0.20,0.00,0.06` on the decided values reproduces the
  decided column to 0.01. Since Stop B (M4) its gate lines print two decimals: `+7.99 (history +8 to +10)`, not
  `+8.0`.

## Children per woman at the decided point

Error 0.71 (today 0.85; the spec's gate was 0.5, which the owner's ruling no longer requires). Incorporated states;
"off" is more than 0.5 from Gapminder:

| Country | 1837 today | 1837 decided | 1837 history | 1887 today | 1887 decided | 1887 history |
|---|---|---|---|---|---|---|
| Argentina | 5.68 | 5.68 off | 6.80 | 5.48 | 5.46 off | 6.14 |
| Austria | 5.32 | 4.97 | 5.10 | – | – | – |
| Belgium | 5.43 | 4.89 | 4.98 | 4.36 | 3.93 | 4.36 |
| Brazil | 5.73 | 5.73 off | 6.26 | 5.19 | 5.19 off | 6.24 |
| Chile | 5.73 | 5.73 | 5.98 | 4.81 | 4.81 | 4.42 (dropped) |
| China | 5.89 | 5.82 | 5.50 (half) | 5.77 | 5.70 | 5.50 (half) |
| Denmark | 5.02 | 4.52 | 4.04 | 5.22 | 5.04 off | 4.28 |
| Egypt | 5.81 | 5.81 | 6.05 | 5.50 | 5.50 off | 6.03 |
| France | 5.13 | 4.63 off | 3.60 | 5.05 | 4.55 off | 3.22 |
| Germany | 5.14 | 4.65 | 4.90 | 4.41 | 3.99 off | 5.23 |
| India | 5.76 | 5.76 | 5.95 | 5.72 | 5.72 | 5.76 |
| Iran | 5.88 | 5.88 off | 7.08 (half) | 5.69 | 5.68 off | 7.08 (half) |
| Italy | 5.57 | 5.24 | 5.47 | 4.89 | 4.61 | 5.03 |
| Japan | 5.57 | 4.46 | 4.54 | 5.38 | 4.28 | 4.04 |
| Korea | 5.87 | 5.80 | – (half) | – | – | – |
| Mexico | 5.79 | 5.79 off | 6.80 (half) | 5.62 | 5.61 off | 6.80 (half) |
| Netherlands | 5.35 | 4.81 | 5.11 | 5.42 | 5.10 | 5.16 |
| Portugal | 5.60 | 5.12 off | 4.50 | 5.54 | 5.14 off | 4.38 |
| Russia | 5.51 | 5.51 off | 7.00 | 5.37 | 5.34 off | 6.61 |
| Spain | 5.65 | 5.26 | 5.13 | 5.34 | 4.97 | 4.78 |
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
- **Germany in 1887** reads 1.2 low. The census's education, urban and means terms already bring it down, and Late
  Marriage compounds them (the spec's §2.3 note on Britain, here worse).
- **Egypt in 1887** reads 0.53 low, against a flat guess near 6.

## China, Manchuria and Korea (D13)

- East Asia's share is **0.06**. The cancel share at no raise is 0, and China projects +6.45 at it, above its band, so
  D13's rule picks the smallest share on the 0.01 grid that brings it inside: 0.06, at +5.93.
- China's children per woman: **5.82 in 1837, 5.70 in 1887**, against history's 5.5 (a flat guess). That is above 5,
  so nothing is flagged.
- Korea: 5.80 in 1837, against a flat 6.0 guess the harness doesn't hold as an anchor.
- India's held share is 0: there is no raise to cancel. India's 5.76 / 5.72 sit on history's 5.95 / 5.76 anyway.

**So Birth Spacing acts fully in Japan** (1.0, cut 0.20: Japan 4.46 / 4.28 against history's 4.54 / 4.04), **and only
slightly in China, Korea and Manchuria** (0.06, about 1% fewer children). That departs from the spec's call 2 (China,
Manchuria, Korea and India at 0.38).

## The means pair

At the offered fallback point every vulcanization and feminism pair from 0.10 to 0.30 gives Britain the same 1887 figure (4.08):
era-3 contraception had not reached Britain by 1887 in this run. The pairs above 0.20 / 0.20 push West 1950, West 1990
with Women's Suffrage and Latin America 1970 out of band. So the pair stays at vulcanization 0.20 and feminism 0.15, and
`te_demog_tech_injections.txt` is unchanged. The fallback's poverty term reaches no scenario and not Britain (SoL above 9),
so the finding holds at the decided point.

## Scenarios and life expectancy at the decided point

- **Fertility scenarios** (`fertility`, now judging each with its practices' shares): all 13 in band. Britain 1836
  4.86, France 1836 4.28, Britain 1900 3.47, West 1950 2.38, West 1990 1.51, India 1975 5.17, East Asia 1990 1.92,
  Latin America 1970 4.03 (its band starts at 4.0).
- **Medicine scenarios** (`medicine`): all in band, unchanged from `main`.
- **Western life expectancy in 1837:** Britain 37.3, Sweden 39.7, Denmark 40.1. Britain fails the 3-year rule, as it
  does today.

## After: the decided build

`practices-replay` and `history --incorporated-only --shares` on the decided values match the decided point's figures
to 0.01: China 5.82 / 5.70, Japan 4.46 / 4.28, Britain 4.69 / 4.08 and Russia 5.51 / 5.34, for example. In the
steady model, 1887:
- Japan is at e0 27.7 (history 37 in 1885) and −0.44% a year. The projection, which holds each state-year's measured
  rates, has Japan growing at +0.3 per 1,000.
- India is at e0 31.2 (history 24 in 1891) and +0.96% a year.
- Britain is at +0.81% (history +0.79%), China at +0.78%.

## The gate, item by item (decided)

| Item | Figure | Verdict |
|---|---|---|
| Each region inside its band | 5 of 12 in; India, Africa, USA and Canada, Middle East, South America, Southeast Asia out, and Europe at +7.99 | **fail** |
| The world at or below today's less 1 per 1,000 | +7.83 against +7.75 or less | **fail** (by 0.08) |
| China +3 to +6 | +5.93 | pass |
| China's children per woman 5 or more (owner, 2026-10-12) | 5.82 / 5.70 | pass |
| No country of 20M+ with births below deaths | none; Japan +0.3 per 1,000 | pass |
| Britain, Sweden, Denmark within 3 years of 41 | 37.3, 39.7, 40.1 | **fail** (Britain) |
| Every fertility and medicine scenario in band | all 13 and all 7 | pass |

## What only calibration step 3 could fix

These regions fail on deaths that standard of living can't place. The fallback's SoL-only refit moved some in and
others out, and a geographic mortality term would separate them. At the decided point:

| Region | Its own children per woman | What it needs, per 1,000 a year |
|---|---|---|
| India | 5.76 / 5.72, history 5.95 / 5.76: right | Deaths up about 2.7 (a tenth; life expectancy 31 against history's 24) |
| Africa | Egypt 5.81 / 5.50 against a guess near 6 | Deaths up about 0.7 |
| Middle East, Central Asia | Persia, Turkey 1.0–1.4 low (flat guesses) | Deaths up about 0.8 |
| South America | Brazil, Argentina 0.5–1.1 low | Deaths down about 0.5, or births up |
| Southeast Asia | no anchor | Deaths down about 0.4 |
| USA and Canada | 5.40, history 6.24 in 1837 | Deaths down (CDR 24.5 against 20–22), **and** births up |
| Europe, the world | | Inside by rounding once any of the above moves |

Japan no longer shrinks, but its life expectancy (27.7 in 1887 against 37) is the same kind of gap: deaths too high
for its SoL.

**A finding, not step 3's:** the USA's births, and the early-marrying world's. A raise of about 1.09 would close the
USA's, but a raise is global. It lifts every early-marrying region the same way, so it fails the gate elsewhere until
step 3 separates their deaths. Once step 3 exists, the raise and the cuts can be refitted with it: the spec's 1.15
gave the least children-per-woman error.

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

The decided values, checked:

```
demographics_harness.py practices-replay SAVES --out REPLAY
demographics_harness.py history S1837 S1887 --anchors A --incorporated-only --shares REPLAY
demographics_harness.py practices-fit SAVES --anchors A --peacetime ROWS --shares REPLAY --s 1.00 --lm 0.10 --bs 0.20 \
  --at 1.00,0.10,0.20,0.00,0.06
```

The re-run of the fit at the fallback's mortality point, and the two-decimal table above, patched the parameters in a
scratch wrapper (`DP.patch_params(POVERTY_INFECTION_AT_FLOOR=2.25, POVERTY_INFECTION_SOL=8)` around the same
functions). Each `practices-fit` reads the eight saves once, in about 4 minutes and 1.1 GB, and a 60-point mortality
grid takes about 8 minutes in all.
