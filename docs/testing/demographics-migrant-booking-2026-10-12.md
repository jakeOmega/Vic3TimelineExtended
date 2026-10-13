# Demographics: what the migration residual is, and how the census books it (2026-10-12)

Phase 2 step 4 (#942) shipped conscription, the youth bulge and sex balance held back, because the census's booking of
the migration residual hollowed out or piled up states' men (37–41% of states at a sex-balance effect in the 1848–1904
saves). This records the diagnosis from the saves, the fix (`demographics_params.py`, "The residual's booking"), and
the bands judged on a re-walk of the run with the fix. Branch `feat/demog-migrant-booking`.

**Status: the residual is the engine's own migration, not unmodelled deaths. Booked with a per-step cap and a
self-correcting labour split, the run's re-walk meets every §5 band of the consequences design's step 4 that can be
judged (the aged society needs phase 3; the 2000 youth band runs on scenarios), and the three effects are on.** The cost is the frontier: no state's men reach 130 per 100 women from migration (below, "The
frontier").

## The data

- **The run:** the overnight normal-speed Full run of 2026-10-12, 1836–1901 (`/mnt/d/vic3te-data/vic3te-demog-overnight-2026-10-12/`),
  main 4002821a (#907, #913, #916). Its 65 yearly saves were extracted by the session's `tools/extract_all.py`
  (`session-notes-2026-10-12/data/*.json`: every state's census variables, bands, rings in 1837/1841/…/1901, pops by
  type and food security).
- **The engine's own migration:** each state record in a save holds `last_week_pop_migration_statistics`
  (`weekly_immigration`, `weekly_emigration` and the states they came from or went to): one week, read from eight
  saves (1847–1849, 1897–1901) and annualised ×52.
- **The second run:** the 2026-10-11 normal-speed Full run (`vic3te-demog-p2-normal-2026-10-11`, 1837–1902), re-walked
  the same way (below).

## Diagnosis: the residual is real migration

The residual is a state's population change less the walk's births and deaths, war dead and kills. Measured three
ways, it is the engine's migration.

| Test | Result |
|---|---|
| The world's residual sums to about 0 (migration does; a booking error wouldn't) | 1848: the states' \|residual\| 5.7M, the world's sum +0.01M; 1898: 12.4M against −1.3M; every year 1840–1900 within ±1.3M against 4.4–12.4M |
| Within countries | 29–53% of the states' gross residual cancels inside its country (38% over the run): internal migration |
| The engine's weekly statistics against the census's residual, per state | 1847–49: Pearson r 0.63; of the 79 states with a residual over 20,000 a year, the engine's sign agrees in 78%; gross 4.6M a year (engine) against 5.2M (census). 1897–1901: r 0.54, 74% of 128, 6.7M against 9.6M. Hyderabad −75k a year against −83k |
| Starving states (over 2% of people starving), the same eight saves | census −8.67M, engine −9.02M: famine-time losses are emigration too |

Starvation is a small part of the out-of-band states' flows: the states below 90 men per 100 women in 1898 (235 by the
bands) took 16% of their outflow in years with over 2% starving, the states at 110 or more 4% of their inflow (1848: 10%
and 6%). Of all booked departures, 10% were in states over 5% starving. **So the brief's first candidate, booking a
famine's negative residual as deaths, would be wrong in kind, and is not built.**

**What went wrong is the booking, year after year.** Vic3 moves whole pops, which have no age or sex: who moved is the
census's overlay, by its migrant profile (labour 90% aged 18–35, women 10–60% by rights and jobs; families and refugees
across ages, half women). In this run 23% of state-years booked over 1% of their people, 14% over 2%, 6% over 5% (the
1st and 99th percentiles −7.8% and +12.3%). A state losing people every year lost them from the same class every year:

- **Hill Punjab** (Patiala): 0.70M in 1837, 0.37M in 1888, with births above deaths throughout: a residual of −2% to −6%
  a year for fifty years, no starvation. Its men per 100 women fell from 94 to 2 by 1870. Delhi, the same country's,
  received them: 0.06M to 1.38M, 157–194 men per 100 women. **West Karelia** 95 to 2 by 1859.
- **Hyderabad** 94 to 45 (1866–1893) and **the Central Provinces** (Nagpur's) 95 to 28 (1898), on −1% to −7% a year.
- **Durango** (Mexico) 94 to 199 and **Wyoming** (USA) 94 to 167 on inflows of 5–17% a year.

The only thing that healed a state was a re-seed (a move of more than a quarter in a year): West Karelia went from 54
to 95 at its 1898 re-seed.

## The fix

Two general rules, in `demographics_model` (`migrant_rates`, `labour_balance_weight`) and the generated script
(`te_demog_migrant_rates`, `te_demog_labour_balance`):

1. **The cap.** In one step the profile adds to a class and sex at most 5% of its people (`MIGRANT_CAP_IN`) and takes at
   most 3% (`MIGRANT_CAP_OUT`); what is left over is booked at one flat rate over every class and sex: whole families
   moving. Below the cap nothing changes.
2. **The labour split corrects itself.** Departures' labour women's share moves to 0.5 as the state's men per 100 women
   fall from 95 to 91; arrivals' as they rise from 105 to 115 (`LABOUR_BALANCE_LOW`, `_HIGH`).

Neither alone is enough (the re-walk, 1898): the cap alone leaves 7.8% of states below 90 and 2.5% at 110 or more
(range 75–123); the correction alone 15.3% and 9.3% (58–124), because a single large year overshoots the correction,
which reads last year's balance.

## The re-walk

`demographics_harness.py rebook SAVE...` (`demographics_rebook.py`) re-walks every census state from the first save's
ring, stepping where the game stepped and seeding where it seeded, each step's residual booked by today's rules and by
the profile alone. The residual doesn't depend on the ring, so it is the run's own. Left out: war dead (tens of
thousands a year at most to 1901) and the mod's kills; the natural rates come from the walk's stored inputs.

**Fidelity** (the profile alone against the saves' own bands): the sex balance's median difference +0.5 (1848) to
+1.4 (1898), 5th–95th percentile −1.9 to +7.0; states outside 90–110: 37.4% in the save, 37.0% re-walked (1848), 41.3%
and 36.7% (1898).

Command (the overnight run; the eight plain-text saves add the transport technologies the family weight reads):
`demographics_harness.py rebook session-notes-2026-10-12/data/*.json saves/autosave.{1791788192,1791789190,1791790503,1791792184,1791794138,1791813114,1791814746,1791816632}.v3`.

| Year | Booking | Below 90 | 110 or more | Range | People with \|T\| past 0.05 / 0.15 | T range | Highest 20–29 share |
|---|---|---|---|---|---|---|---|
| 1848 | profile alone | 17.6% | 19.4% | 23–225 | 26.4% / 13.4% | −0.96 to +0.25 | 0.257 |
| 1848 | booked | 0.0% | 0.6% | 90–111 | 17.9% / 1.6% | −0.13 to +0.25 | 0.177 |
| 1898 | profile alone | 21.6% | 15.2% | 2–213 | 27.7% / 11.8% | −0.96 to +0.25 | 0.240 |
| 1898 | booked | 0.0% | 0.1% | 91–110 | 15.4% / 0.4% | −0.13 to +0.23 | 0.183 |
| 1901 | profile alone | 21.0% | 14.5% | 2–205 | 26.4% / 11.5% | −0.96 to +0.25 | 0.238 |
| 1901 | booked | 0.0% | 0.0% | 91–109 | 14.2% / 0.5% | −0.11 to +0.20 | 0.179 |

With every residual booked flat (no profile at all) 0.9–1.4% of people sit past ±0.05, so the rest of the 14–18% is
the profile's young adults moving, within the cap.

**The margin.** The re-walk's sex balance runs a median +0.5 to +1.4 above the saves' (no war dead, approximate natural
rates), and its emigration states settle at 90–91, where the low ramp completes. In a game they may settle at 89–90,
inside the fewer-men effect at a sliver of its strength: "0.0% below 90" may be a few percent at near-zero strength.
The next run's `consequences` on its own saves is the real test (the play-test list, § The migrant booking, item 2); if
it shows that, moving `LABOUR_BALANCE_LOW` to 96 → 92 is the one-line fix.

**The great powers' conscription terms by decade** (the consequences design's §4.5 gate; booked): Britain −0.02 to
+0.04, France −0.05 to +0.02, Prussia/Germany −0.01 to +0.04, Austria −0.03 to +0.02, Russia 0.00 to +0.03, the USA
+0.01 to +0.05, Sardinia/Italy −0.01 to +0.07, Spain, the Ottomans, Japan, China and British India within ±0.05.
Profile alone: the USA +0.13 to +0.21, Italy −0.13 in 1890, Austria −0.12 in 1860.

The other parameters tried (1898): the low ramp at 93 → 88 left 2.6% of states just below 90, held there; caps of 5%
out and 8% in, 0.4% below 90 and 1.8% at 110 or more (T past 0.15: 2.4% of people); caps of 2% and 3%, none out and
9.3% of people past ±0.05.

## The frontier

Wyoming and North Dakota re-walk to about 101 and 103 men per 100 women in 1898, against 162 and 154 in the save and
about 167 in Wyoming's real 1900 census. Their inflows (5–17% a year) pass the cap and are booked mostly as families. A
setting that keeps frontiers male fails the band: with the arrivals' cap at 10% and the high ramp at 108 → 125, 7.1% of
states sit at 110 or more in 1898 (highest 117); with no arrivals' cap and the ramp at 110 → 140, 15.2% (highest 131).
And the states that go there are not the frontiers: Persia's, Mexico's, Colombia's, Bombay. The census has no signal
that tells a frontier from a city that draws migrants (the destination's female-job share is 0.01–0.05 almost
everywhere before 1900), so this build takes the band, and the "More Men" effect is rare in peace. Whether frontiers
should come back is the owner's call (raise `MIGRANT_CAP_IN` and `LABOUR_BALANCE_HIGH`).

## The second run

The 2026-10-11 normal-speed Full run (`vic3te-demog-p2-normal-2026-10-11`, 66 plain-text yearly saves, 1837–1902; an
earlier build, before #907 and #913), re-walked the same way. **The re-walk reproduces this run less well:** the
profile alone puts 47.3% (1848) and 57.4% (1898) of states outside 90–110 against the saves' 39.0% and 38.9%, and the
5th–95th percentile of its sex balance's difference runs −17 to +38 (the median +0.4 to +0.9). It overstates the old
booking's damage here, so its booked figures are an upper bound, not a band result.

| Year | Booking | Below 90 | 110 or more | Range | People with \|T\| past 0.05 / 0.15 | T range |
|---|---|---|---|---|---|---|
| 1848 | profile alone | 22.4% | 24.9% | 22–250 | 31.7% / 16.5% | −0.96 to +0.25 |
| 1848 | booked | 0.0% | 0.9% | 90–111 | 23.9% / 3.4% | −0.13 to +0.25 |
| 1898 | profile alone | 29.9% | 27.6% | 5–217 | 37.4% / 17.5% | −0.90 to +0.25 |
| 1898 | booked | 0.6% | 1.7% | 88–111 | 17.0% / 4.5% | −0.18 to +0.25 |
| 1902 | profile alone | 28.5% | 26.3% | 14–212 | 44.5% / 15.3% | −0.93 to +0.25 |
| 1902 | booked | 0.5% | 1.7% | 89–111 | 27.4% / 2.6% | −0.15 to +0.25 |

Booked, 2.3% (1898) and 2.2% (1902) of states sit at a sex-balance effect, just over the 2% band, on a re-walk that
runs high for this run. The great powers' terms stay within −0.07 to +0.06 by decade but for Britain, +0.14 in 1890
and +0.10 in 1900 (+0.25 and +0.15 under the profile alone): this run sent Britain large inflows in the 1880s.
