# Regional Climate Warming: the tropics take more, the high latitudes less

Date: 2026-11-13. Issue #1681, split from #1454 by the owner on 2026-11-12. The
issue left three questions to settle before building: what varies by latitude
and by how much, where the variant lives, and how it reads to the player. Every
answer below is the designer's call; the owner may revisit any of them with a
stated reason. Background: `docs/audits/vanilla_1_15_prep.md` § 4.11 and § 7.5,
`docs/systems/mod_systems/global_warming.md`.

## 1. Why

Climate Warming (`global_warming`, `extra_modifiers.txt`) is one modifier
declared once for the world by the contextless World Climate entry (#1448), so
Siberia and the Congo lose the same share of their harvest to the same degree of
warming. The harm of warming is not shared that way. The hottest places already
sit near what people and crops can bear, so each degree costs them most; the
far north starts cold, so warming there shortens winters and lengthens the
growing season as well as burning its forests. Vanilla 1.15's `in_tropics`
(#1672 used it for the disease outbreak's weight) and the Local Climate
record's latitude (`te_climate_latitude`, `local_climate.md`) are enough to say
which states are which.

## 2. Goals and non-goals

**Goals**

1. A state between the tropics takes more of warming's harm than Climate
   Warming gives; a state in the high latitudes takes less, and its farms gain a
   little.
2. The world modifier and everything that reads it (the overview's Warming
   Penalty cell, the UN's adaptation aid, the World Climate self-check, the
   Four Degrees event) stay as they are: mid-latitude states read Climate
   Warming alone.
3. A player can see which band each state is in, and what it costs, without
   leaving the state panel or the climate entry.

**Non-goals**

- A continuous gradient by latitude. Three bands read in one sentence; a
  gradient needs a table per field and a modifier per field (one multiplier
  carries one factor, `scripting_best_practices.md`).
- Bands by local heat, humidity or aridity (the Local Climate record has
  them). Harvest conditions already strike only states vulnerable to them
  (vanilla's `is_vulnerable_to_droughts` and kin), so the drought and flood
  lines of Climate Warming are regional already.
- Hemisphere. The northern hemisphere warms faster, but by a margin far below
  the bands' differences; `in_north_hemisphere` and `in_south_hemisphere` stay
  unused here.
- The AI's climate will (`global_warming_ai_values.txt`). A tropical country
  might want Climate Adaptation sooner; that is a follow-up once the bands have
  been seen in a game.
- Coastal flooding and sea level (`environmentalism_events.9`), which stay on
  the country.

## 3. The bands

Fixed by geography, decided once per state:

| Band | Test | Regions |
|---|---|---|
| Tropics | `in_tropics = yes` (the state region's centre point between the tropics) | about 183 of 676: tropical Africa, most of India south of the Ganges plain, Southeast Asia, Indonesia, the Pacific, Mexico south of the Tropic of Cancer, Central America, the Caribbean, most of South America north of the Tropic of Capricorn |
| High latitudes | not tropical, and the Local Climate record's reference place 55° or more from the equator (`te_climate_abs_latitude >= 55`) | 64: Scandinavia, Finland, the Baltic, Scotland and Ulster, Iceland, Greenland, Russia from Moscow and Kazan north, Siberia, Alaska, northern Canada |
| Mid-latitudes | everything else, and a region with no record | about 430 |

**Why 55° and not 50°** *(designer's call)*. At 50° the band takes in England,
the Low Countries, northern Germany, Poland and Ukraine (132 regions), the
industrial heartland of the nineteenth century, and calls Ukraine's
drought-prone steppe a winner. At 55° it is the boreal north, the region the
literature names when it names warming's gainers. The southern hemisphere has
no land region that far south in the record (the Falklands are at 52°), so the
band is in practice the far north; it is defined by distance from the equator,
so a future region in Tierra del Fuego would join it.

**Why `in_tropics` for the tropics, and the record for the north.** The
tropics band then matches the disease outbreak's weight (#1454), so a state that
draws the outbreak is a state that takes Tropical Warming. There is no vanilla
trigger for the high latitudes. A state near a tropic can fall either way
(`scripting_best_practices.md`, "Latitude Triggers"), which is a matter of a
degree.

## 4. What varies, and by how much

Two state modifiers, per degree of the felt anomaly, **on top of** Climate
Warming; the mid-latitudes carry neither. The totals column is Climate Warming
plus the band. The throughput rows count Climate Warming's −2.5% on every
building, which reaches farms and plantations too.

**Tropical Warming** (`global_warming_tropics`): heat near the limit.

| Line | Band | Total in the tropics | Climate Warming alone |
|---|---|---|---|
| Mortality | +2.5% | +7.5% | +5% |
| Standard of living | −0.5 | −1.5 | −1 |
| Farm throughput (`bg_agriculture`) | −5% | −17.5% | −12.5% |
| Plantation throughput (`bg_plantations`) | −5% | −7.5% | −2.5% |
| Heatwave impact and duration | +25% | +75% | +50% |

Plantations (coffee, cocoa, tea, sugar, rubber, cotton) are where the tropics'
cash crops grow, and Climate Warming has no line of its own for them; heat-sensitive crops
such as coffee and cocoa are among the most exposed.

**High-Latitude Warming** (`global_warming_high_latitudes`): warmer winters,
longer seasons, more fire.

| Line | Band | Total in the high latitudes | Climate Warming alone |
|---|---|---|---|
| Mortality | −3% | +2% | +5% |
| Standard of living | +0.5 | −0.5 | −1 |
| Farm throughput | +14.5% | +2% | −12.5% |
| Frost impact and duration | −15% | −30% | −15% |
| Heatwave impact and duration | −25% | +25% | +50% |
| Wildfire impact | +25% | +75% | +50% |

Wildfire duration stays Climate Warming's alone (+50% everywhere): the World
Climate self-check reads that field to tell whether Climate Warming reached a
country, and `test_vanilla_1_15_opportunities.py` holds it to one carrier.

**The gain.** The issue asked whether the high latitudes gain anything: yes,
farms, a little (+2% a degree with everything counted, +8% at 4 °C), with frost
halved again. The band's farm line is +14.5% because Climate Warming takes
12.5% from a farm a degree (10% from farms and 2.5% from every building); the
first draft's +12% left a net loss of 0.5%, which the review of #1747 caught. The gain
stays small because the same summers dry the soil and burn the forest; the
literature's high-latitude gains turn to losses somewhere past 2–3 °C, which a
modifier scaled linearly can't follow, so the per-degree gain is set low enough
that it stays modest at 4 °C *(designer's call)*.

**The world total.** About a quarter of the world's people lived between the
tropics in 1836 and nearer two fifths by 2000; under a twentieth lived beyond
55°. So the world's summed harm rises: mortality by about a tenth to a sixth
of Climate Warming's, farms and standard of living by about a tenth. That is
the point of the change (the tropics bear more), and it is smaller than the gap
between two tiers *(designer's call)*.

**The death-cause tag.** Each modifier carries `state_death_cause_chr_mult` at
its mortality line's value, as Climate Warming does (Causes of Death files the
climate's heat under chronic illness and old age; `demographics_params.py`).

## 5. Where it lives

An entry can't hold a state modifier, and the contextless World Climate
entry's values may read only globals, so the bands use the dynamic-modifier
pattern on the state (`dynamic_modifier_pattern.md`):

- **One refresh site**, `gw_regional_refresh_effect` (state scope): remove both
  modifiers, store the target in `gw_regional_applied`, add the band's modifier
  at `multiplier = var:gw_regional_applied` when it is above 0. On a state's
  first refresh it also stores the band in `gw_regional_band` (0 mid-latitudes,
  1 tropics, 2 high latitudes), so the latitude chain is read once per state.
  It ends by setting the self-healing marker `gw_regional_rooted` when
  `root ?= this` (`scripting_best_practices.md`, "Add a self-healing marker when
  the apply step has a skip threshold"), so a call with the wrong ROOT is
  redone the next month instead of holding a wrong scale.
- **The target**, `gw_regional_target`: Climate Warming's own scale, the felt
  anomaly (`temperature_anomaly_display`, after any aerosol mask, already in
  hundredths) floored at 0, once the World Climate entry has opened, and 0
  before. The opening is the global flag `gw_g_world_climate_open`, set in
  `global_warming_events_on_action` the first month at 0.1 °C and never
  removed, as the entry never closes; so an aerosol mask that takes the anomaly
  back under 0.1 leaves the bands on with Climate Warming. A first draft
  rounded to 0.05 and cut off below 0.1, which made "the same scale" only
  roughly true (review of #1747).
- **The cadence.** `on_monthly_pulse_state` runs the refresh on a state without
  the marker (a new game's first month, an old save, a newly split state) and
  on a banded state whose stored value differs from the target by more than
  0.005, half the anomaly's step. A mid-latitude state is never touched again.
  A banded state (a few hundred state objects) refreshes in a month when the
  anomaly has moved, every few months at late-game rates, and never runs a
  month behind Climate Warming. A yearly refresh would be cheaper but could run
  a year behind the aerosol mask, which moves within months (§ Geoengineering:
  63% of the way in a year).
- **The rule.** With the Global Warming rule off, the anomaly is held at 0
  (`global_warming_events_on_action`), so the target is 0 and a state that
  carries a band modifier drops it within a month. That is the teardown when
  the rule is switched off mid-game.
- **Owners.** A state modifier stays with the state through a change of owner,
  and the band is the region's, so nothing needs redoing.

**Self-check** (once a game, under the rule, after three months in a row at
0.5 °C or more and not within 0.1 of 1 °C): `TE_SELF_CHECK OK|BROKEN
gw_regional` with the counts of states in each band, of those carrying their
band's modifier, and one tropical state's heatwave duration against its
expected value. OK needs at least 100 tropical states and no more than half of
all states (`in_tropics` reads a band, not everything or nothing), at least 20
high-latitude states, 90% of each band carrying its modifier (the refresh
runs), and the heatwave duration within 0.03 of Climate Warming's 0.5 a degree
plus the band's 0.25 at the state's applied scale (the multiplier reads the
state's variable; a modifier stuck at ×1 reads 0.25 × (1 − scale) away, which
is why a scale near 1 is skipped). Heatwave duration's only other carrier is
the termination shock, so a state whose owner carries it is not read.
Fallbacks: a wrong tropical count, band the tropics by the record's latitude
(under 23.5°) as the north is; a scale off, refresh from a hidden state event,
whose ROOT is the state. Play-test row: `docs/testing/vanilla-1-15-playtest.md`, "1.15
opportunities".

## 6. How it reads to the player

- **The state panel.** A tropical state lists Tropical Warming among its
  modifiers, a high-latitude state High-Latitude Warming, each with its lines at
  today's scale, and the lines show in every breakdown they touch (mortality,
  farm throughput). Neither is hidden: unlike Local Climate, no tile shows them.
- **The Warming Penalty cell's hover** (the climate overview) keeps Climate
  Warming's list and adds both band modifiers' lists, each with the number of
  our states it applies to.
- **The World Climate entry's text and How Global Warming Works** say that the
  bands exist and where.
- **The player guide**, chapter 15, The Climate Warming modifier: the bands, and
  the two totals tables in brief.

## 7. Tests

`test_gw_regional.py`: the two modifiers' lines (the tables above), the death
tag beside each mortality line, the refresh's shape (both removed before
either is added, one call site, the monthly on-action and its trigger), the band
thresholds and the record's count of regions at 55° or more, the loc keys, and
the overview hover naming both modifiers.
