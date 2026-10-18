# Economy growth sim (#1034)

A Python model of how a country's economy grows across the eras under the mod's construction rules, calibrated on one
playthrough's saves. Design: `docs/superpowers/specs/2026-10-17-economy-growth-sim-design.md`. This page holds the
calibration data; the model, its levers and its results are added with the sim itself.

## Data

### Source

`scripts/analysis/econ_series_c480d386.json` is read from playthrough `c480d386`, the owner's 1.14.5 game. Country
id 4 is the player throughout (FRA, the French Commune, FRA again, then EUN), 1836 to 2045.12. It comes from 23
binary saves: `french republic_1867_08_16`, `french commune_1917_10_02`, `_1954_06_21`, `_1954_06_24`,
`_1955_10_06`, `_1959_06_19`, `_1976_01_01`, `france_1986_12_19`, `france_1990_02_24` and 14 `european union_*`
saves from 1998.12.29 to 2045.12.2. Two plain-text saves of the same game (`french commune_1949_07_20`,
`french commune_tmptst`) are skipped: the reader decodes binary saves only.

`scripts/analysis/econ_save_series.py` builds it. Copy each save into a scratch folder first and read the copy,
never the game's save folder, one save at a time:

```bash
PY="python3 -I scripts/analysis/econ_save_series.py"
# 1867 first: its own state lists fix the three sets.
$PY "<scratch>/french republic_1867_08_16.v3" --country-id 4 \
    --core-from "<scratch>/french republic_1867_08_16.v3" --core-id 4 --core-id 1 --core-id 156 \
    --out "<scratch>/x/french republic_1867_08_16.json"
# Every later save, its sets taken from the 1867 extract:
$PY "<scratch>/<save>.v3" --country-id 4 --core-from "<scratch>/x/french republic_1867_08_16.json" \
    --core-id 4 --core-id 1 --core-id 156 --out "<scratch>/x/<save>.json"
# Merge:
$PY "<scratch>"/x/*.json --dataset scripts/analysis/econ_series_c480d386.json
```

A save from another game version, or a plain-text one, prints `skip <name>: <reason>` and the run carries on. Each
save takes 8 to 16 seconds.

### Series

The series follow fixed sets of states, not country ids, because countries change id: a revolution's winner is a
new country object. Great Britain was id 1 in 1867, 50331659 in 1917 and 16777829 from 1954; China was 156, then
16777873. The successors hold most of the old states (28 of Britain's 36 in 1917, 38 of China's 40), but the tags
come and go. So:

- **FRA**, **GBR**, **CHI**: the states that ids 4, 1 and 156 (France, Great Britain, China) held in the 1867 save:
  33, 36 and 40 states. Each point reads that set's pops and buildings, whoever holds them.
- **owner**: the country whose state list holds the most of the set's people at that save (by population, not
  by number of states), with `owner_share`, its share of the set's people. The owner's country fields come with
  the point. GBR's owners are GBR (1, then 50331659), then England (ENG, 33554444 from 1954, 50332331 from
  1986). CHI's are CHI (156, 16777873), then China (ZHO, the mod's formable; 16777873 from 1976, 50331660 from
  1986, 33554467 from 2023).
- **Stop rule**: a GBR or CHI series ends at the first save whose owner is the player (id 4) or holds under half the
  set's people, and that save is left out. GBR ends after 1990.2.24 (EUN holds 84% of it in 1998); CHI never
  stops. FRA, the player's own set, never stops.
- **union**: the player's own states at each save (233 in 1998, 282 in 2045), with per-state figures, so that
  annexations show as states that appear between points.

Points per series: FRA 23, GBR 9, CHI 23, union 23.

### Format

```
{"playthrough": "c480d386",
 "series": {"FRA" | "GBR" | "CHI": {"core_id": 4 | 1 | 156, "core_states": [state ids],
                                    "points": [POINT, ...]},
            "union": {"points": [POINT + "per_state", ...]}},
 "gdp_yearly": {"FRA" | "GBR" | "CHI" | "union": {"<year>": £/yr}},
 "world": [{"date", "gdp", "population"}]}

POINT = {"date", "owner_id", "owner_tag", "owner_share",
         "slice": {"population", "workforce", "peasants", "employed", "unemployed",
                   "wage_per_worker", "welfare_per_unemployed",
                   "buildings_by_type": {type: {"levels", "staffing", "employees", "goods_sales", "goods_cost",
                                                "pms": {pm: levels}}}},
         "owner": {"gdp", "population", "gdppc", "acquired_techs", "investment_by_type", "land_law",
                   "per_project_cap", "variables": {"prior_construction_scaling", "te_mon_gdp_last_year"},
                   "scale", "points_weekly": {"government", "private"}, "pool_spend_weekly"}}
per_state = {state id: [population, workforce, peasants, unemployed, building levels]}
```

- `slice` is a pop and building scan of the set's states. Population is workforce plus dependents. Peasants are
  the workforce of `peasants` pops. Every other pop's workforce is employed when the pop has a workplace and
  unemployed when it has none, since the game keeps a pop's laid-off part in a pop of its own.
  `wage_per_worker` is non-peasant weekly wages (budget slot 0) over employed workers. `welfare_per_unemployed`
  is weekly welfare (slot 3) over unemployed workers, 0 with none. Building money is weekly £.
- `owner` copies the owner's country record: `gdp` (the newest weekly sample of the GDP trend, at its yearly
  rate), `population` (its `pop_statistics`), `gdppc` = gdp / population, the acquired techs, weekly investment
  by building type, the active land-reform law, `per_project_cap` (the largest base speed among the projects
  progressing that week) and two variables. `points_weekly` (construction points a week, per queue) and
  `pool_spend_weekly` (the investment pool's weekly spend on construction) are country-wide flows, so they are
  scaled to the slice: × `scale` = slice population / owner population. A set split between owners therefore gets
  the owner's per-person rate over all its people (GBR 1954: England holds 66% of it, scale 1.51). The union's
  owner fields are unscaled (`scale` 1).
- `gdp_yearly` is the mean of each calendar year's weekly GDP samples of each point's owner. Each sample is taken
  from the first point at or after it, so from the country that held the set at the next save. Samples are
  placed by date: a trend ring's index counts weeks since its own country was created, so a revolution winner's
  starts at 0. Years no owner's ring covers are missing: GBR 1868–1898, CHI 1868–1909 and 1977.
- `world` sums `gdp` and `population` over every country block of the save, including blocks that hold no
  states: a civil war splits a nation's pops between two blocks (below), and each pop is counted once. In 1867
  that sum is 1,345,278,747 people, against 1,345,356,411 from a scan of every pop.
- Building money, staffing, investment and yearly GDP are kept to 2 decimals. The file is 3.19 MB.

### Verification

Against the figures read by hand from the 1917 and 1998 saves:

| check | expected | dataset |
|---|---|---|
| FRA 1917.10.2 population / workforce | 91.07M / 45.55M | 91,069,639 / 45,552,109 |
| FRA 1917 subsisting / unemployed | 10.87M / 6.00M | 10,873,679 / 6,001,809 |
| FRA 1917 construction points a week | 1,954 | 1,954.44 |
| EUN 1998.12.29 population / subsisting / unemployed | 1,198.0M / 208.3M / 94.1M | 1,198,038,722 / 208,299,472 / 94,133,762 |
| EUN 1998 construction points a week | 22,614 | 22,613.78 |
| FRA 1917 union `wage_per_worker` | ≈ £0.092 | £0.0902 |
| FRA set's workforce ≤ id 4's, every save | | all but 1867 |
| union workforce against id 4's `pop_statistics`, every save | within 1% | all but 1867; at most +0.031% |

- The wage figure differs because the hand count divided by the wages of every pop, peasants included:
  (2,585,561 + 58,897 peasants' + 796) / 28,676,702 = 0.0922. Without the peasants it's 0.0902.
- **1867 catches France mid-revolution.** A second FRA block (id 33555011, flagged revolutionary) holds no states
  but 18,106,296 people and £8.25M of GDP. Id 4's own `pop_statistics` and GDP cover only the loyalist 28.7M of the
  46.8M people in France's 33 states. The scans (`slice`, the union) count all 46.8M, so in 1867 they are 1.6×
  id 4's `pop_statistics`. Every later save agrees to within 0.031%. `gdppc` and the scaled flows are per person,
  so the 1867 point needs no special case.

Decoding notes, for the next playthrough:

- A pop's 0x573b, read as "employed" in the 2026-10-17 save probe (`scripts/pops.py`), is not employment: pops
  with no workplace carry it too. Counting with it gives 1.6M unemployed in FRA 1917 against `pop_statistics`'
  6.0M. The workplace (0x330b) gives 6,003,962.
- `pool_spend_weekly` is the opposite of the budget's 0x33c7 (`weekly_investment_pool_change_from_construction`,
  stored negative). FRA 1917: £1.69M a week, 12.4% of GDP over a year.
- A binary save's meta has no ASCII `version`; the version is the string under token 0x00ee.

### The construction-cost penalty in the series

`prior_construction_scaling` (the cost scaling the mod applied at its last yearly pulse) against the raw curve,
clamp((gdp / population − 1) / 99 × 10, 0, 10), at the union's points:

| date | gdp / population | raw curve | prior_construction_scaling | prior / raw |
|---|---|---|---|---|
| 1917.10.2 | 7.77 | 0.683 | 0.666 | 0.975 |
| 1955.10.6 | 14.83 | 1.397 | 1.400 | 1.002 |
| 1976.1.1 | 25.33 | 2.458 | 4.000 | 1.628 |
| 1998.12.29 | 25.04 | 2.429 | 4.409 | 1.815 |
| 2023.11.26 | 58.77 | 5.835 | 10.938 | 1.875 |
| 2045.12.2 | 155.49 | 10.000 | 20.155 | 2.016 |

The 1998 penalty, 4.41, is 1.8 times the raw curve's 2.43 at GDP per capita 25.0. The gap is the country's other
`goods_input_construction_mult`, as the adjusted multiplier intends: `construction_cost_scaling_adjusted_mult`
multiplies the raw curve by one plus every other source, so they compound instead of adding. In EUN 1998 those
sources are the Ministry of the Environment at level 6 and the Ministry of Consumer Protection at level 8 (0.05 a
level each: +0.70), `global_warming` at multiplier 1.31 (+0.066) and `green_building_codes_modifier` (+0.05).
That gives 1 + 0.816 = 1.816, against 4.409 / 2.429 = 1.815. In EUN 2045.12 the same sources sum to +0.995
(levels 8 and 9, warming at 1.9), against 20.155 / 10 = 2.016 at the curve's cap. The ratio is about 1.0 up to
1955 and 1.6 to 2.0 from 1976 on; the sources were read in the 1998 and 2045.12 saves only. It isn't a different
population: the scan's population equals `pop_statistics` at every point but 1867, and at the cap the curve
doesn't depend on population at all. Nor is it a defect in the adjusted multiplier: both saves hold one
`construction_cost_scaling` modifier, whose stored multiplier equals the variable, and in 1998 it was applied on
the save's own date. A model of the penalty therefore needs the ministries' levels, not only GDP per capita.
