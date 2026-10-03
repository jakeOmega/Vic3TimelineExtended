# Drugs wealth probe results — 2026-10-02

**Tester:** Jake, repository owner. **Game:** Victoria 3 1.14.5. **Mod revision:** `5066ccb9`
(branch `feat/drugs-phase-2-healthcare-demand`). **Other mods:** none.
**Probe:** `event te_debug_drugs.1`, fired from the console while paused, straight after
loading each save. Its `TE_DRUGS_PROBE` lines in `debug.log` were copied out as they were
written; nothing was saved afterwards (see [Saving a pre-#500 save](#saving-a-pre-500-save)).

Step 1 of the [phase 2 plan](../superpowers/plans/2026-10-02-drugs-phase-2-healthcare-demand.md).
Its § 2 thresholds are chosen from these tables.

**Read the numbers with these limits:**
- **Every save predates #652.** Pop wealth hardly depends on the Drugs market, so the
  wealth shares stand. The supply and price columns show the *old* Drugs behaviour:
  Pharmaceutical Industries unlocked at `modern_pharmaceuticals` with one method
  (`pm_synthetic_opium`, 100 a level), and the mechanized farm made 75 a level.
- **The saves come from four campaigns,** game versions 1.13.6 to 1.14.5, and older mod
  revisions. The Byzantium saves (1956–2069) are one campaign.
- **There is no save from around 1910.** The owner accepted the gap.
- **The player's country is an outlier from 1883 on,** so the world table also gives each
  save without it.
- **Shares count people** (pop size), not pop objects. "≥25" is the share of a country's
  population living in pops at wealth 25 or more.

## World

Percentage of the world's population at each wealth level or above.

| Save | Date | World pop | ≥10 | ≥15 | ≥20 | ≥25 | ≥30 | ≥35 | ≥40 | ≥50 |
|---|---|---|---|---|---|---|---|---|---|---|
| `greece_1868_08_03` | 1868-08 | 1.35B | 18.1 | 3.8 | 1.9 | 0.77 | 0.51 | 0.38 | 0.11 | 0.02 |
| ↳ without GRE | | 1.34B | 18.0 | 3.7 | 1.9 | 0.77 | 0.51 | 0.37 | 0.11 | 0.01 |
| `khalsa raj_1883_06_05` | 1883-06 | 1.52B | 35.1 | 4.1 | 1.9 | 0.81 | 0.49 | 0.32 | 0.09 | 0.02 |
| ↳ without PAN | | 1.48B | 34.5 | 3.4 | 1.5 | 0.69 | 0.48 | 0.31 | 0.08 | 0.01 |
| `arabia_1949_12_07` | 1949-12 | 3.32B | 92.6 | 26.1 | 6.4 | 3.1 | 1.3 | 0.59 | 0.20 | 0.07 |
| ↳ without ARA | | 3.18B | 92.7 | 23.8 | 4.7 | 1.9 | 0.73 | 0.35 | 0.09 | 0.03 |
| `byzantium_1144_fleetfix` | 1956-10 | 2.14B | 56.5 | 14.2 | 6.1 | 2.3 | 0.87 | 0.44 | 0.24 | 0.16 |
| ↳ without BYZ | | 2.03B | 54.6 | 10.6 | 3.6 | 1.1 | 0.52 | 0.38 | 0.19 | 0.11 |
| `byzantium_1970_12_13` | 1970-12 | 2.41B | 80.4 | 18.9 | 8.5 | 3.7 | 1.3 | 0.51 | 0.34 | 0.21 |
| ↳ without BYZ | | 2.21B | 78.8 | 14.6 | 5.4 | 1.7 | 0.65 | 0.43 | 0.29 | 0.15 |
| `byzantium_1996_05_27` | 1996-05 | 3.30B | 92.8 | 29.1 | 17.3 | 9.7 | 4.7 | 2.0 | 0.76 | 0.23 |
| ↳ without BYZ | | 2.99B | 92.1 | 22.0 | 10.2 | 5.5 | 1.9 | 0.76 | 0.39 | 0.17 |
| `byzantium_2042_10_17` | 2042-10 | 5.12B | 88.4 | 53.4 | 18.2 | 13.1 | 10.1 | 3.5 | 2.2 | 0.54 |
| ↳ without BYZ | | 4.67B | 87.3 | 49.1 | 11.9 | 6.4 | 3.1 | 1.6 | 0.72 | 0.18 |
| `autosave_exit` | 2069-03 | 6.55B | 83.1 | 46.5 | 17.9 | 13.9 | 11.4 | 9.8 | 8.9 | 1.7 |
| ↳ without BYZ | | 6.02B | 81.6 | 41.8 | 10.9 | 6.6 | 3.9 | 2.1 | 1.1 | 0.34 |

From 1949 on, the player's country holds 39–58% of the world's people at wealth 25 or more
(1949: 40M of 102M; 1970: 52M of 89M; 2042: 372M of 670M; 2069: 518M of 912M). At wealth
40 or more it holds 54% in 1996, 70% in 2042 and 89% in 2069.

## Countries

The largest country holding each tag group: North America is `USA`/`FSA`/`UNA`/`CAN`,
Germany `GER`/`NGF`/`PRU`, China `CHI`/`ZHO`, India `BIC`/`BHA`/`BGL`/`MUG`/`IND`. A civil
war's revolt side counts only when nothing else holds the tag. The last row of each save
is the country of 20 million people or more with the lowest share at wealth 15, among those
not already listed. The Drugs price is the country's market price as a multiple of the base
price; 2.00 is the cap.

| Date | Country | Pop | ≥15 | ≥20 | ≥25 | ≥30 | ≥40 | ≥50 | Drugs price |
|---|---|---|---|---|---|---|---|---|---|
| 1868-08 | Greece (GRE) — you | 11M | 11.3 | 2.9 | 0.94 | 0.61 | 0.47 | 0.20 | 0.93 |
| 1868-08 | Great Britain (GBR) | 32M | 11.3 | 4.3 | 1.8 | 1.2 | 0.56 | 0.25 | 0.58 |
| 1868-08 | Free States of America (FSA) | 19M | 11.6 | 4.2 | 1.7 | 0.59 | 0.40 | 0.09 | 1.00 |
| 1868-08 | German Empire (GER) | 36M | 4.5 | 1.5 | 1.0 | 0.82 | 0.11 | 0.07 | 0.93 |
| 1868-08 | Great Qing (CHI) | 494M | 1.9 | 1.5 | 0.53 | 0.46 | 0.02 | 0.00 | 1.17 |
| 1868-08 | Dominion of India (BIC) | 197M | 5.6 | 3.5 | 1.1 | 0.34 | 0.25 | 0.00 | 0.58 |
| 1868-08 | Russia (RUS) | 79M | 5.6 | 1.6 | 0.85 | 0.66 | 0.05 | 0.00 | 1.14 |
| 1868-08 | Tokugawa Shogunate (JAP) — poorest of ≥20M | 43M | 2.6 | 1.5 | 1.0 | 0.55 | 0.23 | 0.01 | 0.88 |
| 1883-06 | Khalsa Raj (PAN) — you | 41M | 28.6 | 18.2 | 5.2 | 0.91 | 0.67 | 0.55 | 0.72 |
| 1883-06 | Great Britain (GBR) | 29M | 5.5 | 1.8 | 0.78 | 0.38 | 0.09 | 0.00 | 0.26 |
| 1883-06 | United States of America (USA) | 41M | 7.8 | 2.2 | 0.94 | 0.33 | 0.13 | 0.01 | 2.00 |
| 1883-06 | German Empire (GER) | 40M | 6.0 | 1.5 | 1.0 | 0.54 | 0.10 | 0.05 | 0.82 |
| 1883-06 | Great Qing (CHI) | 509M | 2.1 | 1.3 | 0.49 | 0.46 | 0.05 | 0.00 | 0.92 |
| 1883-06 | Bengal (BGL) | 79M | 3.1 | 1.6 | 1.4 | 0.48 | 0.17 | 0.01 | 0.64 |
| 1883-06 | Russia (RUS) | 104M | 4.1 | 1.5 | 0.86 | 0.69 | 0.04 | 0.00 | 0.96 |
| 1883-06 | Hyderabad (HYD) — poorest of ≥20M | 22M | 1.9 | 1.3 | 0.46 | 0.36 | 0.05 | 0.01 | 1.10 |
| 1949-12 | Arabia (ARA) — you | 141M | 77.4 | 44.7 | 28.1 | 14.1 | 2.6 | 1.0 | 0.99 |
| 1949-12 | British Republic (GBR) | 29M | 61.6 | 15.4 | 8.7 | 5.0 | 0.60 | 0.03 | 1.15 |
| 1949-12 | United States of America (USA) | 203M | 41.0 | 9.9 | 4.3 | 1.0 | 0.13 | 0.08 | 2.00 |
| 1949-12 | Germany (GER) | 96M | 27.9 | 16.8 | 9.1 | 1.8 | 0.26 | 0.22 | 2.00 |
| 1949-12 | Empire of the Great Qing (ZHO) | 698M | 17.1 | 3.5 | 1.2 | 0.62 | 0.02 | 0.02 | 0.79 |
| 1949-12 | Bengal (BGL) | 168M | 9.5 | 8.0 | 3.9 | 1.1 | 0.15 | 0.03 | 0.61 |
| 1949-12 | Russia (RUS) | 373M | 6.7 | 4.5 | 1.6 | 0.69 | 0.19 | 0.02 | 0.75 |
| 1949-12 | Argentina (ARG) — poorest of ≥20M | 37M | 2.7 | 1.9 | 0.42 | 0.38 | 0.04 | 0.00 | 1.00 |
| 1956-10 | Byzantium (BYZ) — you | 115M | 77.5 | 51.5 | 23.8 | 7.0 | 1.1 | 1.0 | 0.74 |
| 1956-10 | British Republic (GBR) | 38M | 55.1 | 7.1 | 1.3 | 0.39 | 0.05 | 0.00 | 0.58 |
| 1956-10 | Free States of America (FSA) | 89M | 17.7 | 6.2 | 2.2 | 0.89 | 0.64 | 0.52 | 1.21 |
| 1956-10 | German Empire (GER) | 77M | 35.1 | 13.5 | 3.2 | 1.0 | 0.69 | 0.55 | 1.18 |
| 1956-10 | Great Qing (CHI) | 496M | 4.2 | 1.9 | 0.64 | 0.55 | 0.14 | 0.05 | 1.16 |
| 1956-10 | Bengal (BGL) | 103M | 11.8 | 5.0 | 1.3 | 0.53 | 0.33 | 0.08 | 0.62 |
| 1956-10 | Russia (RUS) | 123M | 3.0 | 1.1 | 0.85 | 0.17 | 0.05 | 0.01 | 0.61 |
| 1956-10 | United States of America (USA) — poorest of ≥20M | 74M | 1.9 | 0.90 | 0.40 | 0.19 | 0.05 | 0.01 | 2.00 |
| 1970-12 | Byzantium (BYZ) — you | 193M | 69.0 | 44.6 | 26.8 | 8.8 | 1.0 | 0.84 | 0.81 |
| 1970-12 | British Republic (GBR) | 47M | 60.8 | 9.7 | 2.1 | 0.38 | 0.03 | 0.00 | 0.68 |
| 1970-12 | Free States of America (FSA) | 113M | 23.9 | 8.6 | 2.7 | 1.1 | 0.81 | 0.63 | 0.98 |
| 1970-12 | German Empire (GER) | 79M | 26.2 | 7.5 | 2.7 | 1.3 | 0.85 | 0.60 | 0.97 |
| 1970-12 | Great Qing (CHI) | 565M | 10.3 | 5.4 | 2.0 | 0.74 | 0.44 | 0.16 | 1.03 |
| 1970-12 | Republic of India (BHA) | 208M | 13.1 | 5.4 | 0.93 | 0.48 | 0.12 | 0.09 | 0.73 |
| 1970-12 | Russian Republic (RUS) | 120M | 5.7 | 1.8 | 1.0 | 0.67 | 0.06 | 0.03 | 0.36 |
| 1970-12 | United States of America (USA) — poorest of ≥20M | 90M | 3.8 | 1.4 | 0.35 | 0.25 | 0.04 | 0.02 | 0.83 |
| 1996-05 | Byzantium (BYZ) — you | 319M | 95.2 | 83.2 | 49.1 | 30.8 | 4.2 | 0.81 | 0.68 |
| 1996-05 | British Republic (GBR) | 69M | 46.3 | 5.2 | 1.6 | 0.34 | 0.04 | 0.00 | 2.00 |
| 1996-05 | Free States of America (FSA) | 227M | 20.1 | 12.1 | 7.8 | 1.9 | 0.64 | 0.31 | 1.06 |
| 1996-05 | German Empire (GER) | 72M | 45.8 | 25.9 | 18.7 | 5.1 | 1.4 | 1.1 | 1.06 |
| 1996-05 | Empire of China (ZHO) | 705M | 22.2 | 12.6 | 8.1 | 2.3 | 0.63 | 0.20 | 0.94 |
| 1996-05 | Republic of India (BHA) | 395M | 26.9 | 6.9 | 2.0 | 0.94 | 0.13 | 0.09 | 0.78 |
| 1996-05 | Russian Republic (RUS) | 206M | 5.4 | 2.6 | 0.74 | 0.61 | 0.06 | 0.03 | 0.30 |
| 1996-05 | Iran (PER) — poorest of ≥20M | 40M | 4.7 | 1.8 | 0.77 | 0.34 | 0.09 | 0.05 | 0.30 |
| 2042-10 | Byzantium (BYZ) — you | 444M | 98.8 | 84.6 | 83.9 | 83.6 | 17.3 | 4.3 | 1.14 |
| 2042-10 | British Republic (GBR) | 115M | 50.8 | 0.69 | 0.23 | 0.05 | 0.02 | 0.01 | 1.37 |
| 2042-10 | North American Union (UNA) | 536M | 19.4 | 14.1 | 10.0 | 6.1 | 1.1 | 0.11 | 2.00 |
| 2042-10 | Germany (GER) | 163M | 40.5 | 31.5 | 20.2 | 12.8 | 3.3 | 0.43 | 1.85 |
| 2042-10 | Empire of China (ZHO) | 1255M | 79.3 | 12.3 | 6.1 | 2.3 | 0.43 | 0.22 | 0.93 |
| 2042-10 | Republic of India (BHA) | 708M | 57.2 | 9.6 | 3.7 | 1.3 | 0.07 | 0.06 | 1.04 |
| 2042-10 | Russia (RUS) | 64M | 1.2 | 0.60 | 0.58 | 0.18 | 0.00 | 0.00 | 1.14 |
| 2042-10 | Siberia (SIB) — poorest of ≥20M | 31M | 2.4 | 0.90 | 0.72 | 0.49 | 0.01 | 0.01 | 1.14 |
| 2069-03 | Byzantium (BYZ) — you | 533M | 100.0 | 97.2 | 97.2 | 96.9 | 96.9 | 17.7 | 1.28 |
| 2069-03 | British Republic (GBR) | 183M | 60.4 | 1.7 | 0.40 | 0.15 | 0.03 | 0.00 | 0.84 |
| 2069-03 | North American Union (UNA) | 749M | 22.5 | 16.4 | 10.8 | 6.5 | 2.2 | 0.33 | 2.00 |
| 2069-03 | Germany (GER) | 190M | 75.7 | 30.6 | 25.8 | 16.3 | 8.0 | 3.0 | 1.28 |
| 2069-03 | Empire of China (ZHO) | 1546M | 43.5 | 9.5 | 4.9 | 2.4 | 0.41 | 0.22 | 1.44 |
| 2069-03 | Republic of India (BHA) | 993M | 50.4 | 7.9 | 4.9 | 3.2 | 0.15 | 0.05 | 1.28 |
| 2069-03 | Russia (RUS) | 232M | 4.8 | 1.3 | 0.47 | 0.45 | 0.01 | 0.01 | 1.28 |
| 2069-03 | Philippines (PHI) — poorest of ≥20M | 36M | 1.4 | 0.68 | 0.38 | 0.26 | 0.00 | 0.00 | 1.00 |

## Drugs supply and market

Levels are world totals. The output share weights each level by its method's output before
#652 (basic plantation 20, irrigation 40, mechanized farm 75, Pharmaceutical Industries
100), at full staffing and with no throughput modifiers. Buy and sell orders are summed over
every market that trades Drugs.

| Date | Plantation levels (basic / irrigation / mechanized) | Pharma levels | Pharma share of output (est.) | World buy orders | World sell orders | Buy ÷ sell | Qing bans Drugs |
|---|---|---|---|---|---|---|---|
| 1868-08 | 456 / 0 / 0 | 0 | 0.0% | 9,285 | 14,676 | 0.63 | no |
| 1883-06 | 260 / 6 / 0 | 0 | 0.0% | 4,685 | 7,898 | 0.59 | yes |
| 1949-12 | 174 / 211 / 258 | 10 | 3.1% | 28,739 | 45,301 | 0.63 | no |
| 1956-10 | 493 / 611 / 0 | 0 | 0.0% | 37,979 | 66,541 | 0.57 | no |
| 1970-12 | 301 / 883 / 55 | 0 | 0.0% | 49,342 | 79,067 | 0.62 | no |
| 1996-05 | 101 / 84 / 1212 | 0 | 0.0% | 125,060 | 189,316 | 0.66 | no |
| 2042-10 | 24 / 114 / 2433 | 12 | 0.6% | 470,382 | 433,803 | 1.08 | no |
| 2069-03 | 199 / 88 / 2400 | 12 | 0.6% | 1,603,119 | 825,976 | 1.94 | no |

## Qing and Pharmaceutical Industries under phase 1 (1868 → 1878)

| | 1868 (loaded) | 1876 (after about eight years under #652) |
|---|---|---|
| Qing Pharmaceutical Industries levels | 0 | 0 |
| Qing opium plantation levels | 72 | 85 |
| Qing bans Drugs | no | no |
| Drugs price in Qing's market | 1.17 | 1.16 |
| World Pharmaceutical Industries levels | 0 | 2 |
| World plantation levels | 456 | 490 |
| World buy ÷ sell orders | 0.63 | 0.63 |

Countries with Pharmaceutical Industries in 1876: Cuba (CUB) 1, Great Britain (GBR) 1.
By method in 1876: `pharma_alkaloid` 2.

Run on the 1868 save under the current mod, mod revision `5066ccb9`: loaded, played into
1876 at top speed, probed. Qing built no Pharmaceutical Industries in about eight years and
added 13 plantation levels; the first two levels in the world went up in Great Britain and
Cuba.

## Readings

Observations the owner chose the curve from (decisions below).

- **Wealth 25 is rare until late.** Under 1% of the world through 1883, 2–4% from 1949 to
  1970 (1–2% without the player), 10% by 1996 (5.5% without) and 13–14% from 2042 (6–7%
  without).
- **The tail above 30 is thin.** Wealth 40 or more stays under 1% of the world except in
  2042 (2.2%) and 2069 (8.9%), and without the player it never passes 1.1%.
- **AI countries rarely get rich.** In 2069 only Germany (26% at wealth 25) and North
  America (11%) are well above the floor. China and India reach about 5%; Great Britain and
  Russia stay under 0.5%.
- **So a need keyed at wealth 25 lands largely on the player.** Two-fifths to three-fifths of
  the world's wealth-25 population is the player's from 1949 on, and nearly all of its wealth-40
  population by 2069. The plan's starting curve (about 15 at wealth 25, 40 at 30, the cap of
  60 at 40) would be paid almost entirely by the player's country and two or three AI
  countries.
- **The old Drugs market was oversupplied until the 2040s, then short.** Buy orders were
  about 0.6 of sell orders through 1996, 1.08 in 2042 and 1.94 in 2069, before any
  healthcare demand. Pharmaceutical Industries made at most 3% of supply in any save; #652's
  earlier unlock is what changes that, and § 4 checks it.
- **Qing banned Drugs only in the 1883 save.**
- **Leisure buys Drugs too (found after the decisions; open question).** Vanilla's Leisure need
  lists Drugs (weight 0.5 of 10.1, at most half the need) and declares the obsession fields.
  In the buy packages Leisure is 394 at wealth 40, 9,648 at 60 and 442,526 at 100, so a rich
  pop's Drugs demand keeps growing long after Healthcare's cap of 60. That works against the
  goal that the ultra-wealthy don't buy orders of magnitude more, and it may be part of the
  2069 shortage, when Byzantium had 97% of its people at wealth 40 or more. Whether to cut or
  cap Drugs in Leisure (`REPLACE:popneed_leisure`) is the owner's call.

## Saving a pre-#500 save

Saving `greece_1868_08_03.v3` after the first version of the probe had run crashed the game
twice, at the same fault address (`EXCEPTION_ACCESS_VIOLATION` at `0x00007FF772CB275A`; crash
folders `victoria3_01260902_164104` and `_164330`). Loading that save logs 428 unresolved
`building_resettlement_camp` references; #500 deleted that building and assumed old saves
holding it would still load. Every save here from before 2042 holds camps. The suspected
cause is saving a game that still holds those camps, not the probe. Not yet confirmed: load
the same save, save it without firing the probe, and see whether it crashes.

## Decisions (owner, 2026-10-02)

- **Curve:** the plan's starting curve. No Healthcare demand below wealth 20, about 15 at
  wealth 25, about 40 at 30, and the cap of 60 from wealth 40 up.
- **Intoxicants:** Drugs keep their weight of 0.75 for now, so the § 4 play-forward shows
  Healthcare's own effect on the price. It can come down afterwards.
- **Plantation penalties:** on `building_opium_plantation_throughput_add`, the only
  plantation-only lever (`goods_output_opium_mult` applies per good and would cut
  Pharmaceutical Industries too). Per investment level of the Ministry of Health
  (`institution_health_system`): Charity Hospitals −2%, Private Health Insurance −3%, Public
  Health Insurance −5%; and per level of the Ministry of Consumer Protection −10%. The mod's institution cap is 9 levels, so the two together reach −135%; a
  plantation's other throughput bonuses cushion that.
- **Follow-ups, each in its own PR:** a UN drug convention modelled on the 1961 Single
  Convention, and a random event with a high chance of firing while Drugs are short, in
  place of a scaled mortality modifier.
