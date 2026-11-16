# Extraplanetary Base per-good grades: a score for each good at every site, and the order bases fill room — design

Drafted 2026-11-05 with the owner. It changes the Extraplanetary Base room of
`2026-10-25-solar-colonization-modules-and-bases-design.md` § 9 (one grade per
site) and the base methods of `2026-10-29-lunar-colonization-design.md` § 6.
A draft for the owner's review: the scores in § 6 are a first guess, and § 8
lists the calls still open.

## 1. The owner's calls (2026-11-05)

1. **A score per good at every site**, in place of each site's single
   Extraplanetary Base grade. It began with a question: why Regolith Processing
   makes Glass and Plastics while the later mining methods make none.
2. **Scope the fill order carefully.** Today a country's built levels always
   take the best room first. With a score per good, one site can yield more
   goods while another yields goods worth more on the market right now.

## 2. What one grade does today

- `gen_solar_sites.SITES` gives each site an `ebase_grade` in percent, from +30
  at 16 Psyche to −45 at Sedna; the near-Earth asteroids' 10 levels sit at 0.
- `sr_ebase_refresh` (`sr_colony_module_effects.txt`, monthly, the one refresh
  site) fills the country's built levels into its room in a fixed order, best
  grade first (`ebase_tiers()`, generated into `sr_ebase_fill`). Levels past
  all of it take −75%.
- The average over all levels becomes one country modifier,
  `sr_ebase_room_bonus` or `sr_ebase_room_penalty`
  (`building_space_mine_throughput_add`, ±1% a unit). Throughput scales inputs
  and outputs alike, so a grade moves a level's profit by the same percent.
- `sr_ebase_next_fill` stores the grade the next level would work at, for the
  overview's Base Room cell. The Modules view prints each site's room and grade.
  The 40 per-site tooltips (`je_space_race_widget_bases_tt_<site>`) are
  hand-written loc and state each grade in words.

Nothing else reads the grade. The AI's build gate reads room, not grade.

## 3. Two layers: richness as throughput, the mix as output

### 3.1 Why not output multipliers alone

An output multiplier leaves the inputs alone, and these methods spend most of
their output's value on Launch Capacity. On the Asteroid Mine (£37,250 out,
£30,000 in, at base prices):

| | As throughput (today) | As an output multiplier |
|---|---|---|
| 16 Psyche, +30% | £9,425 a level (+30% profit) | £18,425 (+154%) |
| Past the room, −75% | £1,812 | −£20,688 |

Profit moves by output value ÷ profit times the multiplier: about 10× on
Regolith Processing, 5× on the Asteroid Mine, 4× on the Mining Colony and
1.8× on Self-Replicating Miners. Today's grades as output multipliers would
break the balance, and no single rescaling fixes it.

### 3.2 The model

Each site `w` has a score `s(w,g)` for each good `g`. Its **overall grade**
`G(w)` is the value-weighted mean of its scores over the shared basket (§ 4)
at base prices, rounded to a whole percent. Every grade in § 6's draft rounds
to today's, so the fill order, the throughput and every test of the grades stay
as they are.

Monthly, the fill gives each level a site, as today. Over the country's `L`
levels:

- `T` = the average of `G` over the levels, levels past the room at −75%:
  today's country throughput modifier, unchanged.
- `S(g)` = the average of `s(·,g)` over the levels, levels past the room at −75%
  for every good.
- `D(g)` = `(1 + S(g)) ÷ (1 + T) − 1`: an output multiplier for each good.

A level's output of `g` is then its base output × `(1 + T)(1 + D(g))` = base ×
`(1 + S(g))`, the site's score, and its inputs scale by `(1 + T)` alone. For a
method whose outputs follow the shared basket, the `D(g)` cancel in value at
base prices, so a level at site `w` earns `(1 + G(w))` times the method's base
profit: today's figure at every site. The mix changes what a base makes, not
what it earns at base prices. What it earns at the prices of the day is § 5's
question.

This assumes the engine multiplies throughput and a goods output multiplier
rather than adding them. If it adds them, `D(g)` = `S(g) − T` instead. The
play-test settles it by reading one base's output tooltip (§ 7).

### 3.3 Where the modifiers go

- **`T` stays the country modifier it is today.**
  `building_space_mine_throughput_add` reaches only bases.
- **`D(g)` goes on each Extraplanetary Base building, not the country.** A
  country's `goods_output_iron_mult` would raise every Structural Metals
  producer it owns. The refresh adds `D(g)` from the country pulse, as the
  Space Command's upkeep is added (`sr_fl_upkeep_apply`,
  `sr_fleet_effects.txt`): `every_scope_state` → `every_scope_building` with
  `is_building_type = building_space_mine`, remove first, then
  `multiplier = root.var:sr_ebase_mix_<good>`. Buildings hold no variables
  (`scripting_best_practices.md`), so the figures live on the country.
- **Twelve unit modifiers**, a bonus and a penalty for each good
  (`goods_output_<good>_mult` ±0.01). All six types are registered already
  (`mod_entity_modifier_types.txt`). Each needs loc and a Nation tab registry
  line (`NOT_ON_COUNTRY`, `gen_nation_tab.py`).
- **The removal pass covers every base a country owns**, with or without
  In-Situ Resource Utilization, so a captured base sheds its old owner's mix.
- **Other output multipliers on a base add to `D(g)`**, so a stack is a sum,
  not a product. One reaches a base today: Vale's prosperity bonus
  (`company_vale`, +10% Structural Metals output for its whole country,
  `extra_companies_flavored.txt`). At Titan, where `D` for Structural Metals is
  −67%, Vale's country would run −57%: 0.43 of base output where a product
  would give 0.33 × 1.1 = 0.36. That is small enough to accept. The colony specializations and discoveries carry throughput or
  Advanced Materials, and stay as they are.

## 4. One basket for the four mining methods

A site's mix can scale only the goods a method already makes. Today Regolith
Processing makes Structural Metals, Tech-Critical Metals and Glass and
Plastics, and the later methods make Gold, Structural Metals, Conductive and
Base Metals, Chemical and Industrial Minerals and Tech-Critical Metals. With two
baskets, a glass-rich site is worth more under Regolith Processing than under
the Asteroid Mine, and the `D(g)` cancel for only one of them.

So the four mining methods share one basket: the same six goods in the same
shares of output value at base prices. Each keeps its output value, its inputs
and its crew. Today's outputs are in brackets.

| Good | Share | Regolith Processing | Asteroid Mine | Mining Colony | Self-Replicating Miners |
|---|---|---|---|---|---|
| Structural Metals | 24% | 100 (175) | 225 (250) | 900 (1,000) | 1,125 (1,250) |
| Tech-Critical Metals | 44% | 91 (95) | 205 (250) | 820 (1,000) | 1,025 (1,250) |
| Gold | 12% | 20 (none) | 45 (50) | 180 (200) | 225 (250) |
| Conductive and Base Metals | 5% | 21 (none) | 45 (25) | 180 (100) | 225 (125) |
| Chemical and Industrial Minerals | 5% | 16 (none) | 39 (25) | 156 (100) | 195 (125) |
| Glass and Plastics | 10% | 42 (50) | 90 (none) | 360 (none) | 450 (none) |
| Output value | | £16,600 | £37,250 | £149,000 | £186,250 |

- **Every profit stays put**: the figures in `test_deep_sea_rebalance.py` and
  `production_methods.md`, Regolith Processing's £1,600 and 2.0 a worker. The
  Mining Colony stays four Asteroid Mines and Self-Replicating Miners five.
  Rounding leaves each method's shares within half a point of the basket's.
- **Tech-Critical Metals fall** from 54% of the later methods' output value to
  44%, about a fifth fewer a level. Conductive and Base Metals and Chemical and
  Industrial Minerals rise.
- **Every mining method makes Glass and Plastics**, as much as the ground
  holds: next to none at 16 Psyche, a lot on Titan, where the good's plastics
  half fits.
- **One test conflicts.** `test_era_11_outputs_each_at_least_the_asteroid_mine`
  holds Global Commons § 1.1's rule that the era-11 Deep-Sea Mine makes at
  least as much of every good as the Asteroid Mine. The Deep-Sea Mine makes no
  Glass and Plastics (call 2).
- **The Resort Colony** makes art and tourism, which get no score. It works
  at the overall grade, as today.

## 5. The fill order

### 5.1 What the order decides

- The average runs over the levels, so the order decides only which room is
  used and which is left empty. Past all of a country's room every site is in
  use, and the order doesn't matter.
- Room is large next to most bases (50 to 300 levels a site, 4,325 in all). A
  country's levels usually sit in its best one or two sites, so the order
  decides the base's whole mix.
- The property the owner set on 2026-10-25 (`16-space.md`): a new poor colony
  adds room without lowering what the levels earn, and only levels past the
  room pay the penalty. Any fill that takes the best room first, by a fixed
  measure, keeps it, because one more site can only raise what the best `L`
  levels earn. Spreading levels over all held room in proportion to it would
  remove the order question but break this property, so it is rejected.

### 5.2 The measure is money; the question is which prices

"More goods" is the overall grade, which is throughput: more of every input
too. It is better only through what the goods sell for. So the measure is a
level's profit, and the question is at which prices. For a method `m` with
input-to-output ratio `c(m)` at base prices, and price changes `π` (a fraction
of base price, as `market_goods_pricier` reads them), a level at site `w` earns
in proportion to

    Σ_g share(g) × (1 + s(w,g)) × (1 + π(g))  −  c(m) × (1 + G(w)) × (1 + π_inputs(m))

At base prices that is `(1 + G(w))(1 − c(m))`, the grade, for every method.
So today's order is the profit order at base prices, and it stays so under § 4.

At the prices of the day it depends on the margin. A thin margin makes
the mix dominate. The best site among all 41 under one price move each, from
§ 6's scores, inputs at base prices except where named:

| Method | Price move | Best site | Its profit a level over 16 Psyche's |
|---|---|---|---|
| Regolith Processing (era 10) | Glass and Plastics +50% | Titan | +134% (£2,906 a week) |
| Regolith Processing | Chemical and Industrial Minerals +75% | Venus Cloud Habitat | +88% (£2,122 a week) |
| Regolith Processing | Tech-Critical Metals −30% | Venus Cloud Habitat | £1,484 a week; Psyche loses money |
| Regolith Processing | Launch Capacity +50% | Sedna | £3,307 a week; Psyche loses money |
| Asteroid Mine (era 11) | Glass and Plastics +50% | Titan | +51% (£4,869 a week) |
| Asteroid Mine | Chemical and Industrial Minerals +75% | Venus Cloud Habitat | +32% (£3,294 a week) |
| Asteroid Mine | Tech-Critical Metals −30% | Venus Cloud Habitat | +73% (£1,862 a week) |
| Asteroid Mine | Launch Capacity +50% | Sedna | £3,570 a week; Psyche loses money |
| Mining Colony (era 12) | Glass and Plastics +50% | Titan | +32% (£15,870 a week) |
| Mining Colony | Chemical and Industrial Minerals +75% | Ceres | +21% (£10,728 a week) |
| Mining Colony | Tech-Critical Metals −30% | Venus Cloud Habitat | +21% (£4,237 a week) |
| Mining Colony | Launch Capacity +50% | Sedna | £8,268 a week; Psyche loses money |
| Mining Colony, both logistics upgrades | Glass and Plastics +50% | Ceres | +3% (£3,595 a week) |
| Mining Colony, both logistics upgrades | Chemical and Industrial Minerals +75% | Ceres | +2% (£2,031 a week) |
| Mining Colony, both logistics upgrades | Tech-Critical Metals −30%, or Launch Capacity +50% | 16 Psyche | none |
| Self-Replicating Miners (era 13) | Glass and Plastics +50% | Ceres | +5% (£6,638 a week) |
| Self-Replicating Miners | Chemical and Industrial Minerals +75% | Ceres | +3% (£4,683 a week) |
| Self-Replicating Miners | Tech-Critical Metals −30%, or Launch Capacity +50% | 16 Psyche | none |

Read across:

- **Once margins are wide** (both logistics upgrades, Self-Replicating
  Miners), richness rules: a fixed order gives up 2% to 5%.
- **On the era-10 to 12 methods before the upgrades**, one good 50% dear can
  make another site worth a third to a half more a level than Psyche: £15,870
  a week a level for an era-12 Mining Colony.
- **When Launch Capacity is dear enough that every level loses money**, profit
  ranks the poorest site first (Sedna), because its low throughput loses least.

### 5.3 The options

- **A. A fixed order by overall grade** (today's). No new runtime logic, easy to
  read, no feedback through prices. It ignores the prices of the day and leaves
  § 5.2's gains unearned.
- **B. A player priority per colony** (High, Normal, Low) on top of A. Cheap
  and stable. The player has to chase prices by hand, which the owner's
  micromanagement default (2026-10-16) warns against, and the AI never uses it.
- **C. An automatic ranking by profit at the prices of the day.** Earns
  § 5.2's gains with no player work. It costs a runtime sort, smoothed prices
  and a guard against oscillation (§ 5.5).

### 5.4 Recommendation: C, built after the scores ship on A

PR 1 ships the per-good scores on today's fixed order (A). PR 1 is needed
whichever order wins, and it keeps every current guarantee. PR 2 replaces the
order:

- **Prices**: monthly, each country smooths the six goods' price changes and
  its bases' input price change into variables (weight 1/36 a month, about a
  three-year average). Each is read signed, as the Strategic Reserve reads its
  goods (`st_res_<good>_price_rel`; `scripting_best_practices.md` § "Is it
  signed below base price?").
- **Methods**: the ranking weights each method by the levels running it
  (`has_active_production_method`). The generator writes each method's `c(m)`
  and input weights from the production method files, and a test keeps them in
  step.
- **Ranking**: yearly, and in the month a country gains or loses a site, each
  held site's profit per level goes into `sr_eb_key_<site>`, and the sites are
  ranked into `sr_eb_rank_<site>`. That is O(N²) generated script once a year
  for each country with bases.
- **Margin**: a new ranking is adopted only if the levels as they stand would
  earn at least 10% more under it.
- **Guard**: if no site earns money per level, the grade order stands (call 5).
- **Fill**: monthly by rank instead of the fixed tier order, as a `while` over
  the ranks that stops when the levels run out, usually after one to three
  sites.
- **Display**: the Base Room cell names the site the next level would work
  ("next: Titan, −15%"). A notice can say when the ranking moves the base
  (call 6).
- **Old saves and revolutions**: with no ranks yet, the grade order stands.
  Ranks and smoothed prices are variables, so a revolution's winner keeps them.

### 5.5 Oscillation

The base moves to its best site all at once, so a large base can move its own
market. It moves to Titan, Glass and Plastics fall, and Psyche is best again: a
cobweb cycle. Three-year smoothing, a yearly ranking and the 10% margin together
allow at most one move a year, and only once the gain outlasts the move's own
effect on prices. If the play-test shows a base cycling anyway, the fallback is
a stateful fill. Each site keeps its levels (a variable per site), and a
ranking moves only a share of them, a third a year, so the mix adjusts instead
of jumping. That costs a variable per site for each country and more script, so
it isn't proposed for the first build.

## 6. Draft per-good scores

Each site starts from a relative composition: how much of each good its ground
holds next to the basket. The composition is scaled so the value-weighted mean
over the basket equals today's grade. A site rich in some goods is therefore
poorer in others, and its grade, its place in the order and its profit at base
prices don't move. Every derived grade is within 0.37 of today's and rounds to
it. The scores are in percent, a level's output of that good against the
method's base output.

| Site | Grade | Structural | Tech-Critical | Gold | Conductive and Base | Chemical and Industrial | Glass and Plastics | Character |
|---|---|---|---|---|---|---|---|---|
| Near-Earth asteroids | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The reference: the basket as it comes |
| Shackleton Crater | 0 | −1 | −13 | −63 | −26 | +123 | +86 | Cold-trapped polar volatiles |
| Peary Crater | 0 | +10 | −14 | −63 | −26 | +60 | +96 | Sunlit highlands, some ice |
| Tranquility Base | +5 | +51 | +4 | −72 | −43 | −25 | +32 | Ilmenite mare basalt: iron and titanium |
| Marius Hills | +5 | +37 | −5 | −68 | −26 | +5 | +79 | Basalt and volcanic glass beads |
| Daedalus Crater | 0 | +28 | −18 | −65 | −42 | −18 | +121 | Far-side highland anorthosite |
| Mare Imbrium | 0 | −16 | +34 | −75 | −41 | +17 | −8 | KREEP: rare earths, phosphorus, potassium |
| Valles Marineris | +10 | +49 | −4 | −26 | +17 | +59 | −4 | Exposed strata: hematite, sulfates, clays |
| Olympus Mons | +10 | +38 | −8 | −42 | +4 | +38 | +73 | Basalt flows and lava tubes |
| Hellas Planitia | +10 | +39 | −7 | −30 | +16 | +51 | +39 | Deep basin sediments |
| Utopia Planitia | +10 | +37 | −13 | −38 | 0 | +50 | +87 | Ice-rich sediments |
| Arcadia Planitia | +10 | +39 | −12 | −37 | +1 | +127 | +39 | Brines and their salts |
| Ceres | +15 | −21 | −6 | −37 | −6 | +246 | +151 | Brines, carbonates, ammoniated clays, organics |
| 4 Vesta | +20 | +38 | +15 | −8 | +3 | −20 | +61 | Basaltic crust, the mantle bared at Rheasilvia |
| 16 Psyche | +30 | +61 | +40 | +72 | +8 | −46 | −89 | Iron-nickel, platinum-group metals, gold |
| 2 Pallas | +10 | −11 | +1 | −24 | +1 | +90 | +103 | Hydrated silicates |
| 10 Hygiea | +5 | −22 | −9 | −35 | −9 | +108 | +134 | Carbonaceous |
| Io | −5 | −9 | −18 | −27 | +9 | +218 | −27 | Sulfur volcanism |
| Europa | −5 | −39 | −24 | −55 | −9 | +279 | +82 | Sulfate salts on ice |
| Ganymede | 0 | −5 | −5 | −41 | −5 | +42 | +66 | Rock and ice |
| Callisto | 0 | −13 | −13 | −38 | −13 | +50 | +112 | Carbon-rich dust |
| Himalia | +5 | −14 | −1 | −26 | −1 | +73 | +85 | A captured carbonaceous asteroid |
| Amalthea | 0 | −11 | −11 | −36 | +2 | +180 | +27 | Red with Io's sulfur |
| Venus Cloud Habitat | −10 | −72 | −57 | −86 | −57 | +398 | +256 | No ground: sulfuric acid and carbon dioxide from the clouds |
| Mercury | +5 | +25 | +7 | −11 | −2 | +42 | −47 | Sulfur-rich crust over an iron core |
| Titan | −15 | −72 | −58 | −86 | −58 | +124 | +348 | Hydrocarbon lakes and tholins: plastics feedstock |
| Enceladus | −20 | −59 | −46 | −73 | −46 | +170 | +170 | Plume salts, silica, organics |
| Rhea | −15 | −25 | −25 | −50 | −25 | +26 | +76 | Mostly ice |
| Mimas | −20 | −28 | −28 | −52 | −28 | +20 | +56 | Mostly ice |
| Iapetus | −20 | −40 | −40 | −64 | −40 | +32 | +152 | A dark organic hemisphere |
| Titania | −25 | −25 | −25 | −50 | −25 | −17 | 0 | Half rock |
| Oberon | −25 | −29 | −29 | −56 | −29 | −11 | +33 | Rock and dark material |
| Miranda | −30 | −38 | −22 | −53 | −38 | −30 | −14 | Exposed layers |
| Ariel | −30 | −44 | −34 | −62 | −34 | +50 | +22 | Cryovolcanic ammonia |
| Triton | −30 | −38 | −30 | −61 | −38 | +16 | +9 | Nitrogen geysers over rock |
| Proteus | −35 | −45 | −37 | −61 | −45 | −14 | +25 | Dark and irregular |
| Pluto-Charon | −35 | −47 | −40 | −62 | −47 | +5 | +35 | Tholins, nitrogen and methane ice |
| Eris | −40 | −46 | −40 | −60 | −46 | −26 | −6 | Methane frost on rock |
| Makemake | −40 | −55 | −48 | −70 | −55 | −18 | +64 | Methane and ethane ices |
| Haumea | −40 | −40 | −34 | −58 | −46 | −52 | −34 | Dense rock under crystalline ice |
| Sedna | −45 | −59 | −52 | −72 | −59 | −31 | +51 | Red tholins |

The patterns, for a quicker review than row by row:

- **The Moon** is poor in Gold and base metals and rich in Glass and Plastics,
  with volatiles at the poles. Its iron and titanium are in the maria
  (Tranquility Base) and its Tech-Critical Metals are in Mare Imbrium's KREEP.
- **16 Psyche** is the metals site and holds almost no Glass and Plastics.
  **Mars** is iron oxides and sulfates.
- **The carbonaceous asteroids and the icy moons** lean to Chemical and
  Industrial Minerals and Glass and Plastics.
- **Io and Europa** are the sulfur sites. **Titan** is the plastics site, and
  the **Venus Cloud Habitat** has no ground to mine.
- **Past Saturn** the best each site has is its organics, at a grade that
  leaves little of anything.

The generator would store the scores, which are what players see, and derive the
grade from them. `test_solar_sites.py`'s table rules (the range, Psyche best, the
outer stages poorer on average) then run on the derived grade. A score is never
below −100%: a site with none of a good makes none.

## 7. What changes

**PR 1: the scores on today's order.**

- `gen_solar_sites.py`: the per-good scores in `SITES`, the derived grade,
  `sr_ebase_fill` summing each good as well as the grade, and the Modules view
  rows. It also generates the 40 base tooltips, each with its site's mix, in
  place of the hand-written loc.
- `sr_ebase_refresh`: the six `D(g)` and the per-building apply and removal pass
  (§ 3.3).
- `space_race_modifiers.txt`: the twelve unit modifiers, their loc and their
  Nation tab registry lines.
- `extra_pms.txt`: the shared basket (§ 4). The cost comments are rewritten by
  `pm_costs` on reload.
- Tests: `test_solar_sites.py` (the table and the per-good sums);
  `test_deep_sea_rebalance.py` (the basket, the era-11 comparison per call 2;
  Regolith Processing's £1,600 and 2.0 unchanged).
- Self-check `TE_SELF_CHECK ebase_mix`: a base carries the `D(g)` it was given
  (`docs/testing/solar-colonies-playtest.md`). Play-test item: a base at 16
  Psyche shows Tech-Critical Metals at base × `(1 + T)(1 + D)`, which settles
  multiply against add (§ 3.2).
- Docs: `space_race.md`, `production_methods.md`, the player guide's
  § Extraplanetary Base room (the grade table becomes overall grades, and each
  site's mix is in its hover), `02-timeline.md` (Regolith Processing's goods),
  the PDF, and the Base Grade concept.

**PR 2: the ranking (§ 5.4).**

- Generated: the per-site profit values, the yearly ranking, the margin test, the
  fill by rank and the next-level display.
- Hand-written: the monthly price smoothing, the method weights and the notice.
- Tests for the ranking's structure, and a play-test item that watches a large
  base for cycling (§ 5.5).

## 8. Calls for the owner

1. **The shared basket's shares** (§ 4). Tech-Critical Metals fall from 54% to
   44% of the later methods' output value.
2. **The era-11 Deep-Sea comparison and Glass and Plastics.** Either compare
   only the goods the Deep-Sea Mine makes, or keep Glass and Plastics off the
   Asteroid Mine. The second leaves its `D(g)` far from cancelling: with the
   other five goods at the basket's proportions, an Asteroid Mine level makes
   40% less output value on Titan than its grade says, 30% less at the Venus
   Cloud Habitat and 21% less on Enceladus, and 13% more at 16 Psyche. Comparing
   only the shared goods is the recommendation.
3. **The Resort Colony stays on the overall grade**, with no scores for art or
   tourism.
4. **The order**: C after A, as recommended (§ 5.4); or A alone; or B.
5. **The guard**: when every site loses money per level, keep the grade order,
   or let the ranking pick the site that loses least.
6. **A notice when the ranking moves the base**, or a quiet move shown only in
   the Base Room cell.
7. **The scores themselves** (§ 6).
