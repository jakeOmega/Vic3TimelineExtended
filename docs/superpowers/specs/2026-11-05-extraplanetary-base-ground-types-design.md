# Extraplanetary Base ground types and where the levels work: design

Drafted 2026-11-05 as a score for each good at all 41 sites and an automatic,
price-aware fill order. Rewritten 2026-11-21 after the review and the brief on
PR #1397, and after the owner's answers to this rewrite's questions. It
replaces the single grade a site of
`2026-10-25-solar-colonization-modules-and-bases-design.md` § 9 with a grade and
a ground type, gives the four mining methods of
`2026-10-29-lunar-colonization-design.md` § 6 one basket of goods, and puts the
choice of where a country's levels work in a panel. § 12 records the owner's
answers to its calls (2026-11-21); the appendix maps each point of the review
to where this document answers it.

**Built** (2026-11-21, `feature/ebase-ground-types`, one PR as § 10 planned). Where
the build differs from the text below, the build is right and the section says so:
the moves run once a calendar month (§ 8.2, § 8.5); switching the checkbox off
gives each site the levels it will hold once every blockade has returned (§ 8.4);
profit a level and the yardstick count the cuts the base's other method groups
make to its inputs (§ 8.3); the Bases view's layout fits its column (§ 9.1); the
per-type hovers are hand-written (§ 9.2); the Base Room cell names the next site
alone (§ 9.3); the notice counts its 5% by the pair of types, and the move record
gives years (§ 9.4). The Resort Colony
left the building first (#1950), so the four mining methods are the base's only
methods and § 7's fallback for a resort that stays is moot. § 4 describes the
base before this build.

## 1. The owner's calls

**2026-11-05**, when the first draft was written:

1. Sites should differ in the goods they hold, not only in how rich they are.
   The question that started it: why Regolith Processing makes Glass and
   Plastics while the later mining methods make none.
2. Scope the fill order carefully. Today a country's levels always take the
   best room first; once sites hold different goods, one site can yield more
   while another yields goods worth more on the market.

**2026-11-21**, from the brief posted to the PR after the owner talked the
review through. The owner likes sites holding different resources and is fine
with complexity, but was worried the first draft was more of it than the
trade-offs justify unless it could be shown clearly. Decided:

3. **About six ground types** in place of 41 × 6 scores. Each type has one fixed
   mix, and a site is its type and its grade.
4. **An assignment panel** in place of the price-aware ranking. In the owner's
   words (as the brief gives them): a panel that shows the per-level output of
   Extraplanetary Bases at each site, where you assign levels to sites when you
   have fewer levels than room. With 100 levels of room at a tech-metal site A,
   100 at a structural-metal site B and 150 levels built, you can put 100 and
   50, 50 and 100, 75 and 75, or anything else, and see what the production
   would be.
5. **A checkbox that reassigns levels for the most profit**, on by default.
   The AI always uses it; assigning by hand is opt-in.
6. **The bases share the result evenly by level**: the two layers of § 5 (the
   grade as throughput on the country, the mix as an output multiplier on each
   building) and the shared basket of § 7 stay.
7. **The choice is real.** In the owner's experience several of these goods are
   in demand late in the game, though one or two sometimes fall to very low
   prices, so the checkbox has real work to do when a good gluts.

**2026-11-21**, the owner's answers to this rewrite's questions:

8. **Every move is paced.** Whether the player or the checkbox decides where
   levels should work, levels already placed move there at one fixed pace (§ 8.5).
   New levels go straight to their place. Switching the checkbox off and on
   gains nothing, and a large base can't flip its own market in a month.
9. **Unassigned levels fill by grade**, as today.
10. **A blockaded or occupied site keeps its levels on record.** They work
    elsewhere meanwhile and return when the site is freed.
11. **Each site shows its profit a level** at current prices, beside its output
    a level.
12. **The Deep-Sea comparison takes a second exception**, for Glass and
    Plastics (§ 7). The owner on that test: it formalizes a general guideline
    that each of these buildings has a place, and it can be changed to match a
    new design. A change to it should be deliberate, and the PR should say in a
    short section how the new balance is meant to work, but the test doesn't
    block the design.
13. **One or two implementation PRs.** The owner will likely wait for all of it
    before a release, so fewer PRs are fine if that saves effort (§ 10).

## 2. The goal: three questions a player can answer from the UI

The owner's worry was complexity the player can't see. The test this design is
built to pass, and the play-test item for it: **from the UI alone, can a player
say where their levels work, what the base makes, and why it last moved?** Each
reading in § 9 answers one of the three. A mechanic that no reading explains is
out of scope.

## 3. Approaches

- **A. A score for each good at every site, with an automatic yearly ranking by
  profit** (the first draft). It has the most detail, but its inputs were
  invisible (smoothed prices, method weights, a 10% margin), so its moves would
  have read as bugs, and the player had no way to say no. Set aside by the
  owner on 2026-11-21.
- **B. Ground types, an assignment panel and a profit checkbox** (this design).
  A site reads as a word and a grade. Where the levels work is on the screen,
  set by hand or by the checkbox, and the checkbox's rule fits in one line.
- **C. Ground types on today's fixed order by grade, with no choice.** The
  simplest. But it leaves the gains when a good gluts unearned, and those gains
  are the reason for the mix.

The owner chose B.

## 4. What one grade did before this build

- `gen_solar_sites.SITES` gives each site an `ebase_grade` in percent, from +30
  at 16 Psyche to −45 at Sedna, and an `ebase_room` of 50 to 300 levels, plus
  50 a staffed Mining Complex level (`sr_site_ebase_room_<key>`). The
  near-Earth asteroids give 10 levels at 0 with Asteroid Mining
  (`NEAR_EARTH_ROOM`, `NEAR_EARTH_TECH`).
- `sr_ebase_refresh` (`sr_colony_module_effects.txt`) runs from the monthly
  country pulse and the day after a base is built or gains a level
  (`space_race_events.110`). It is the one refresh site. It fills the country's
  built levels into the room of the sites that serve it (`site_serves`: held,
  not blockaded, not occupied) best grade first (`sr_ebase_fill`, generated in
  `ebase_tiers()` order). Levels past all of it work at −75% (`OVERFLOW_GRADE`).
- The average over all levels is one country modifier, `sr_ebase_room_bonus` or
  `sr_ebase_room_penalty` (`building_space_mine_throughput_add`, ±1% a unit).
  Throughput scales inputs and outputs alike, so a grade moves a level's profit
  by the same percent.
- `sr_ebase_next_fill` stores the grade the next level would work at, counting
  queued levels, for the overview's Base Room cell. The Modules view and the
  Solar System view print each site's room and grade
  (`module_bases`/`module_grade`, `site_bases`). The 40 per-site hovers
  (`je_space_race_widget_bases_tt_<site>`) are hand-written loc.

Nothing else reads the grade. The AI's build gate (`sr_ebase_may_build_*`)
reads room, not grade, and stays as it is.

## 5. Two layers: the grade as throughput, the mix as output

### 5.1 Why not output multipliers alone

An output multiplier leaves the inputs alone, and these methods spend most of
their output's value on inputs. On the Asteroid Mine (£37,250 out, £30,000 in,
a week at base prices):

| | As throughput (today) | As an output multiplier |
|---|---|---|
| 16 Psyche, +30% | £9,425 a level (+30% profit) | £18,425 (+154%) |
| Past the room, −75% | £1,812 | −£20,688 |

So the grade stays throughput, and only the mix is an output multiplier.

### 5.2 The model

Over the country's `L` levels, with `n(w)` working at site `w`, its grade `G(w)`,
and its type's mix `m(t, g)` for good `g` (§ 6):

- `T` = the average of `G` over the levels, levels past the room at −75%. That is
  today's country throughput modifier, unchanged.
- `1 + D(g)` = Σ `n(w)(1 + G(w))(1 + m(t(w), g))` ÷ Σ `n(w)(1 + G(w))`. In words,
  the base's mix is the average of its sites' types' mixes, each weighted by the
  levels working there times (1 + its grade). Levels past the room count as the
  neutral type, Mixed.

A level then makes base × `(1 + T)(1 + D(g))` of each good and uses base ×
`(1 + T)` of each input. Summed over the base, that is exactly
Σ `n(w)` × base × `(1 + G(w))(1 + m(t(w), g))`: each level makes what its own
site's ground gives.

Two consequences that make the building readable (review point 1):

- **A base whose levels all work ground of one type shows exactly that type's
  mix on its buildings, and its grade as throughput.** A base at 16 Psyche alone
  carries +30% throughput and Glass and Plastics −91%, the Metallic mix. That
  holds across sites of one type with different grades too.
- **At base prices a site earns exactly `(1 + G)` times a level's base profit**,
  as today, because every type's mix averages to zero over the basket (§ 6.1).
  The mix changes what a base makes, not what it earns at base prices.

**Multiply, not add.** This assumes the engine multiplies throughput and a goods
output multiplier. `scripting_best_practices.md` § "A Building's `modifier:`
Read Carries Its Country's Lines, and Throughput Scales Script-Set Goods Lines"
measured that throughput scales goods lines set by script-applied `_mult`
modifiers (the Grid Transfer Stations, #1248). So the product form is the
expected one, and a play-test item confirms it on a base (§ 10).

### 5.3 Where the modifiers go

- **`T` stays the country modifier it is today.**
  `building_space_mine_throughput_add` reaches only bases.
- **`D(g)` goes on each Extraplanetary Base building, not on the country.** A
  country's `goods_output_iron_mult` would raise every Structural Metals
  producer it owns. The refresh adds it from the country pulse, as the Grand
  Monument's upkeep is added (`gm_effects.txt`, `multiplier =
  root.var:gm_upkeep_mult`) and the Space Command's (`sr_fl_upkeep_apply`):
  `every_scope_state` → `every_scope_building` with `is_building_type =
  building_space_mine`, remove first, then `multiplier =
  root.var:sr_ebase_mix_<good>`. Buildings hold no variables, so the figures
  live on the country.
- **Fourteen unit modifiers**, a bonus and a penalty for each of the seven goods
  (`goods_output_<good>_mult` ±0.01). The engine generates
  `goods_output_<good>_mult` for every good (`/engine-docs/origin/goods_output_lead_mult`
  finds it under vanilla's `goods_output` mask). Six have their display entry
  in `mod_entity_modifier_types.txt`; `goods_output_lead_mult` needs one. Each
  modifier needs loc and a Nation tab registry line (`NOT_ON_COUNTRY`,
  `gen_nation_tab.py`).
- **The removal pass covers every base a country owns**, with or without
  In-Situ Resource Utilization, so a captured base sheds its old owner's mix.
  Both of the refresh's triggers fire only for a country with the technology
  (the monthly pulse in `space_race_on_actions.txt`, and `space_race_events.110`),
  so the pulse's gate widens to "has the technology, or owns a base". Without
  the technology the refresh only removes.
- **A level built since the last refresh** may arrive without the building's
  modifiers. The refresh the day after a level finishes
  (`space_race_events.110`) re-applies them on every base, as it already
  re-applies `T`.
- **Other output multipliers on a base add to `D(g)`**, so a stack is a sum, not
  a product. Three reach a base today: Vale's prosperity bonus (`company_vale`,
  +10% Structural Metals output for its whole country), and two unique mines'
  +5% for their state, `pm_vale_carajas_mine` (Structural Metals) and
  `pm_bhp_mount_whaleback_mine` (Conductive Metals, `unique_pms.txt`). That is
  small enough to accept, and figures in the UI are given to the whole percent, no finer than
  the engine delivers (review, smaller notes).
- **Other throughput on the bases** (Commercial Space Industry, orbital debris,
  colony specializations) adds to `T`. It scales every site alike, so it shifts
  which site is best only where two sites' grades differ and their profits are
  within a few percent. It is left out of the profit a level of § 8.3.

## 6. Ground types

### 6.1 The model

A site's score for a good is `s(w, g)` = `(1 + G(w))(1 + m(t, g)) − 1`, where
`t` is its ground type. Each type's mix is scaled so that its value-weighted
mean over the basket (§ 7) is exactly zero. A site's grade is then exactly its
value-weighted mean score, with no rounding argument. A type rich in some goods
is poorer in others, and the grade alone carries how much a site yields
overall. The generator stores each type's composition and normalizes it. A
test holds every type's mean to zero and every derived grade to the site's.

The mixes start from the first draft's 41 rows: each type's figures are a
rounded version of the average of its sites' rows, put back on the new
seven-good basket (Conductive and Base Metals took the old combined column's
figure, adjusted where the ground says otherwise, such as nickel on Psyche).

### 6.2 The seven types

Percent against the basket, a level's output of that good against the
method's base output at grade 0. Rounded to the whole percent.

| Type | Structural | Tech-Critical | Gold | Conductive | Base | Chemical and Industrial | Glass and Plastics | Best when | The ground |
|---|---|---|---|---|---|---|---|---|---|
| Mixed | 0 | 0 | 0 | 0 | 0 | 0 | 0 | The reference | The basket as it comes: the near-Earth asteroids |
| Metallic | +12 | +2 | +30 | +12 | −7 | −72 | −91 | Gold dear; Chemical and Industrial Minerals or Glass and Plastics cheap | Iron-nickel, platinum-group metals, gold |
| Rocky | +26 | −3 | −51 | −17 | −17 | +7 | +36 | Structural Metals dear | Basalt and other silicate rock: iron, titanium, aluminum, glass |
| Carbonaceous | −17 | −7 | −33 | −7 | −7 | +107 | +117 | Chemical and Industrial Minerals and Glass and Plastics both dear | Clays, carbonates, ammonia, organics |
| Sulfurous | −16 | −11 | −37 | +5 | +5 | +320 | +26 | Chemical and Industrial Minerals dear | Sulfur, sulfates, sulfuric acid |
| Hydrocarbon | −25 | −15 | −50 | −20 | −20 | +80 | +249 | Glass and Plastics dear; Tech-Critical Metals cheap | Hydrocarbon lakes, tholins, organic ices |
| Icy | 0 | −5 | −40 | −10 | −10 | +61 | +81 | No one good: the middle of the road | Water ice over rock, with some volatiles |

Base Metals are 1% of the basket's value, so no type leans on them: the seabed
is where they come from (Global Commons). Gold is the asteroids' metal, which
is why every type but Metallic is poor in it.

### 6.3 The sites

Grades are today's, so the order by grade, the room and every test of the
grades stay as they are.

| Type | Sites (grade) |
|---|---|
| Mixed | The near-Earth asteroids (0) |
| Metallic | 16 Psyche (+30) |
| Rocky | 4 Vesta (+20); Valles Marineris, Olympus Mons, Hellas Planitia (+10); Mercury, Tranquility Base, Marius Hills (+5); Daedalus Crater, Mare Imbrium (0) |
| Carbonaceous | Ceres (+15); 2 Pallas (+10); 10 Hygiea, Himalia (+5); Callisto (0); Enceladus (−20) |
| Sulfurous | Amalthea (0); Io, Europa (−5); Venus Cloud Habitat (−10) |
| Hydrocarbon | Titan (−15); Iapetus (−20); Pluto-Charon (−35); Makemake (−40); Sedna (−45) |
| Icy | Utopia Planitia, Arcadia Planitia (+10); Shackleton Crater, Peary Crater, Ganymede (0); Rhea (−15); Mimas (−20); Titania, Oberon (−25); Miranda, Ariel, Triton (−30); Proteus (−35); Eris, Haumea (−40) |

Three sites as scores, for a feel of the range: 16 Psyche makes +45% Structural
Metals, +33% Tech-Critical Metals, +69% Gold and −88% Glass and Plastics;
Titan −36%, −28%, −58% and +197%; Ceres −5%, +7%, −23% and +150%, with +138%
Chemical and Industrial Minerals.

Sites whose character changed from the first draft are in § 12, answer 3.

### 6.4 What the types do at the prices of the day

A level's profit at site `w` is `(1 + G(w))` × its type's margin at today's
prices. So **among sites of one type the better grade always wins**, and the
choice is only ever between types. The best type under one price move at a
time, on the Asteroid Mine (era 11), inputs at base prices; the last two
columns compare six sites, a week a level:

| Price move | Best type at equal grade | Its edge over Mixed | Best of Psyche, Vesta, Ceres, Io, Titan, Ganymede | Its profit, and Psyche's |
|---|---|---|---|---|
| None | All equal | 0 | 16 Psyche | £9,425 |
| Structural Metals +50% | Rocky | +11% | 16 Psyche | £16,686 |
| Tech-Critical Metals +50% | Metallic | +1% | 16 Psyche | £18,743 |
| Tech-Critical Metals −30% | Hydrocarbon | +21% | Ceres and Psyche, a tie | £3,841; Psyche £3,834 |
| Gold +50% | Metallic | +8% | 16 Psyche | £13,661 |
| Chemical and Industrial Minerals +75% | Sulfurous | +37% | Io | £10,630; Psyche £9,765 |
| Glass and Plastics +50% | Hydrocarbon | +40% | Ceres | £11,835; Psyche £9,594 |
| Glass and Plastics −50% | Metallic | +22% | 16 Psyche | £9,256 |

Read across:

- **The margin decides how much the mix matters.** On Regolith Processing
  (era 10, an 11% margin) the same moves give edges of up to +70% over Mixed,
  and with Glass and Plastics +50% Ceres earns 58% more a level than Psyche. On
  Self-Replicating Miners (era 13, a 127% margin) the edges are 1% to 16%, and
  Psyche is best under every move but that one (Ceres, +1%). So the choice
  matters most in eras 10 to 12 and in a glut, and the grade decides once
  margins are wide. That fits the owner's call 7 (§ 1): the checkbox has its work
  when a good falls.
- **A rich site of a so-so type often beats a poor site of the right type.**
  Ceres, Carbonaceous at +15%, is the best place for Glass and Plastics among
  these six, ahead of Titan, Hydrocarbon at −15%.
- **Icy is never the best for one good alone.** It is a hedge, and most of its
  sites are poor, so the type mostly says what the site is (§ 12, answer 2).

## 7. One basket for the four mining methods

A site's mix can scale only the goods a method already makes. With two
baskets, a glass-rich site would be worth more under Regolith Processing than
under the Asteroid Mine, and `D(g)` would not cancel at base prices for one of
them. So the four mining methods share one basket: the same seven goods in the
same shares of output value at base prices. Each keeps its output value, its
inputs and its crew. Today's outputs on `main` are in brackets.

| Good | Share | Regolith Processing | Asteroid Mine | Mining Colony | Self-Replicating Miners |
|---|---|---|---|---|---|
| Structural Metals | 26.9% | 111.41 (175) | 250 (250) | 1,000 (1,000) | 1,250 (1,250) |
| Tech-Critical Metals | 37.6% | 78.00 (95) | 175 (210) | 700 (840) | 875 (1,050) |
| Gold | 13.4% | 22.27 (none) | 50 (50) | 200 (200) | 250 (250) |
| Conductive Metals | 10.2% | 42.34 (none) | 95 (95) | 380 (380) | 475 (475) |
| Base Metals | 1.1% | 4.46 (none) | 10 (10) | 40 (40) | 50 (50) |
| Chemical and Industrial Minerals | 3.4% | 11.14 (none) | 25 (25) | 100 (100) | 125 (125) |
| Glass and Plastics | 7.5% | 31.19 (50) | 70 (none) | 280 (none) | 350 (none) |
| Output value | | £16,600 | £37,250 | £149,000 | £186,250 |

The basket is the Asteroid Mine's outputs on `main`, with 7.5% of the value moved
from Tech-Critical Metals to Glass and Plastics at equal value, as the
2026-11-15 change moved Conductive Metals' share. The bases already oversupply
Tech-Critical Metals: in the late hand-played game behind that change, a country
fed by its bases covered its Tech-Critical demand one and a half times over (the
comment above `pm_space_mine` in `extra_pms.txt`). Conductive Metals stay a tenth
of each method's sales, the owner's 2026-11-15 floor that
`test_deep_sea_rebalance.py`'s `ExtraplanetaryBaseMix` holds.

- **Every profit stays put**: Regolith Processing's £1,600 and 2.0 a worker, the
  figures in `test_deep_sea_rebalance.py` and `production_methods.md`. The
  Mining Colony stays four Asteroid Mines and Self-Replicating Miners five.
- **Regolith Processing's outputs have two decimals**, the basket scaled to its
  £16,600 exactly. Whole numbers would leave its shares up to 0.3 points off,
  and on its 11% margin that is enough to matter: Chemical and Industrial
  Minerals 0.25 points over would alone give a Sulfurous site about 8% more
  profit at base prices, past the checkbox's margin. With two decimals every
  type earns £1,600 a level at grade 0 and base prices to within £0.50.
- **What changes on update, by method** (review point 6), for the build PR's
  description (the release notes are written from it) and the player guide:
  - Regolith Processing: Structural Metals −36%, Tech-Critical Metals −18%,
    Glass and Plastics −38%, and it now makes Gold, Conductive Metals, Base
    Metals and Chemical and Industrial Minerals.
  - Asteroid Mine, Mining Colony and Self-Replicating Miners: Tech-Critical
    Metals −17%, and they now make Glass and Plastics. Every other good is
    unchanged.
  - Every site's output then follows its type (§ 6), so a base's actual change
    depends on where it works.
- **The Deep-Sea comparison** (owner's call 12). The era-11 Deep-Sea Mine makes no
  Glass and Plastics, so
  `test_era_11_outputs_each_at_least_the_asteroid_mine_but_tech_critical`
  takes a second exception, `glass`, beside `tech_metals`. The intended balance,
  for the implementation PR's section: the Deep-Sea Mine is the cheaper,
  Earth-bound source of the bulk metals and makes at least as much of each of
  them as an Asteroid Mine (Structural 320 against 250, Conductive 230 against
  95, Base 50 against 10, Chemical and Industrial 50 against 25, Gold 50 against
  50). The asteroids are where Tech-Critical Metals come from, and the bases
  also make Glass and Plastics, which the seabed can't: it has no plastics
  feedstock. The test's two other checks (input cost and crew) are unchanged.
- **The Resort Colony leaves this building.** The owner may move it to a building
  type of its own (2026-11-21), as another session's work (#1948), so this design
  assumes the four mining methods are the only ones in its base group. A resort's
  draw has nothing to do with ore, and it works at the mining grade today, which
  makes 16 Psyche, the richest metal mine, the best resort. If it stays instead,
  it works at the grade with no mix, and the checkbox's profit a level weights
  it in by its share of levels.

## 8. Where the levels work

### 8.1 What a country stores

All of it is in country variables, so a revolution's winner keeps it (the
winner continues the nation). For each of the 41 places (the 40 sites and the
near-Earth asteroids, `near_earth`):

- `sr_eb_at_<k>`: the levels working there now.
- `sr_eb_target_<k>`: the levels the player wants there, used only while the
  checkbox is off.
- `sr_eb_away_<k>`: levels moved out because the site stopped serving us
  (blockade or occupation), owed back when it serves again.

And once per country:

- `sr_eb_manual`: set while the checkbox is off. Unset means on, which is the
  default and the AI's.
- `sr_eb_placed`: set at the first placement. A country without it places all its
  levels at once (§ 8.8).
- The panel's lines (§ 9.1): the current move's source and destination sites
  and the month it began, and the "at target" or "if prices hold" totals.

### 8.2 The month

`sr_ebase_refresh` keeps its two triggers, with the monthly one's gate widened
(§ 5.3), and stays the one refresh site. Each run:

1. **Room**: each place's room that serves us this run (`site_serves`, as today;
   0 otherwise).
2. **Displacement, at once**: where `at` exceeds the room, the excess leaves. If
   the site stopped serving us, it goes into `away`. Either way it is placed as
   new levels are (step 4). A site lost for good (ceded, captured, abandoned)
   loses its `at`, `target` and `away`.
3. **Return, at once**: a site that serves us again takes back up to its `away`,
   from levels past the room first, then from wherever the checkbox (or, with
   it off, the order by grade) would take levels from first (step 5).
4. **Levels gained or lost**: the built total `L` against the sum of `at` and the
   levels past the room. New levels go straight to their place. With the
   checkbox on, that is the best site with free room by profit a level, if that
   site makes money; otherwise the order by grade. With it off, it is sites
   below their target first, best grade first, then by grade (owner's call 9).
   Lost levels come off the levels past the room first, then the site the next
   move would take from. **Levels past the room move into room that opens** (a
   colony founded or seized, a Mining Complex staffed) the same way and at
   once, whichever mode is on. Today's fill does the same, and pacing them would
   hold levels at −75% for months, against § 8.6.
5. **Moves, paced** (§ 8.5): up to the month's pace in levels move from one site
   to another. With the checkbox on, a level moves from the worst site in use to
   the best site with room, by profit a level, while the move clears the margin
   (§ 8.3). With it off, it moves from a site above its target to one below it.
   A level no rule calls for stays where it works.
6. **The modifiers**: `T` and the seven `D(g)` from the `at` counts (§ 5), and
   `sr_ebase_next_*` for the overview cell (§ 9.3).

Steps 2 to 4 only follow what happened (a blockade, a cession, a level built or
lost, room gained), so they are not paced. Only step 5's choices are.

**As built, step 5 runs once a calendar month** (`sr_eb_moved_month`). Steps 1 to 4
and 6 run on every refresh, the monthly pulse and the day after a level is built,
and change nothing when repeated on the same inputs; the moves and the move record
wait for the month's first run, so a build day never spends a second month's pace.
A first placement made mid-month moves from the next month, as the model's "placed
before this month" says.

### 8.3 The checkbox

With the checkbox on, each month moves levels from the site in use that earns
least a level to the site with free room that earns most. It moves only while
the gap is at least **5% of the yardstick**, which is our methods' profit a
level at grade 0 and base prices, weighted by their levels (£7,250 for an
Asteroid Mine, £21,650 with both era-12 logistics upgrades: see below). The
yardstick is fixed, so the rule behaves the same when profits are small or negative. It
never moves levels to a site that loses money a level. When every site loses
money, nothing moves, and the panel says why (§ 9.1). The two alternatives
both chase something worse. Least loss sends the base to the poorest sites,
since low throughput buys fewer inputs, which reads as a bug. Most revenue
sends it to the richest. A level's inputs scale with its grade, and Launch
Capacity, 80% of a base's input cost, is what makes every site lose. So more
revenue raises the base's demand for the very input that is too dear, keeps its
price up longer and deepens the loss. It would also jump at the switch, from
the best profit to the best revenue, often a different site. Holding still
waits for the price to come back.

**Profit a level** at site `w` of type `t`:

    (1 + G(w)) × Σ_m f(m) × [ Σ_g out(m, g) × p(g) × (1 + mix(t, g))  −  Σ_i in(m, i) × p(i) ]

Here `f(m)` is the share of our levels running method `m` (read with
`has_active_production_method`), and `p` is this month's price on our own
market. **As built, each input term also carries the cuts the base's other method
groups make to it** (the build's review, 2026-11-21): Tethered Launch and Fusion Tugs
each take 30% off a level's Launch Capacity, about 80% of its input bill, so a
level's inputs are `in(m, i)` × (1 + the sum of its building's active
`goods_input_<i>_mult`), weighted by levels as `f(m)` is. Left out, from era 12 the
rule overweighted the ground type against the grade and could call every site a
loser when none was. The yardstick counts the cuts too, since it is our methods'
profit a level: with both, the move margin on an Asteroid Mine is about £1,083.
Digital Access is local, and is read at the market's price. The price reads:
`market = { mg:<good> = { market_goods_pricier / market_goods_cheaper } }`
times the base price, read the way `st_res_<good>_price_rel` reads it. The
generator writes
each method's outputs and inputs from the production method files, and a test
keeps them in step.

**It is cheap.** Profit a level is `(1 + G)` × the type's margin, so the
month computes seven margins and multiplies. Finding the best site with room
and the worst in use is one pass over the 41 places each.

**Why moving at the margin rather than chasing a plan.** A rule that sets
targets to the best fill at today's prices and moves toward them overshoots. It
plans the whole base onto Ceres, prices respond while the levels travel, and the
plan flips back, a slow cycle. Moving only while the best site beats the worst
by the margin stops by itself once the base's own supply has closed the gap.
That happens inside the margin, with no flip, because the pace is slow next to
how fast a market price responds. This replaces the first draft's three-year
price smoothing, yearly ranking and 10% plan margin. The checkbox reads
unsmoothed prices.

### 8.4 Assigning by hand

- **Switching the checkbox off** sets every site's `target` to its `at` and its
  `away`, so nothing moves until the player changes one. **As built**, the targets
  are the levels each site will hold once every blockade has returned: a blockaded
  site its `at` and `away`, and the others less the levels the return will take
  from them (all of `away` past what `over` covers), worst profit a level first.
  With `at` alone, a blockaded site's levels came back at once and then moved out
  again at the pace. With `at` and `away` alone, the displaced levels were
  assigned twice, at the site they work and at the site that owes them, so +
  stayed greyed and the return left targets no move would reach (final review,
  2026-11-21). The buttons read the same targets while the checkbox is on.
- **The − and + buttons** on a site's row change its `target`. Minus stops at 0.
  Plus stops at the site's room, and only works while some levels are
  unassigned, that is while the targets sum to less than built plus queued
  levels. The tooltip says why when it can't (`gui_style_guide.md` rule 6).
  Counting queued levels lets a player place levels before they are finished.
- **A click while the checkbox is on** switches it off first, keeping where the
  levels are as the starting targets.
- **Switching the checkbox back on** drops the targets. The checkbox's moves
  then start from where the levels are, at the same pace.
- **Unassigned levels** (built and queued minus the targets) are placed by
  grade when they arrive (owner's call 9). Those already working stay where
  they are.
- **Step sizes**: 5 levels a click and 25 a right-click
  (`onrightclick` on a scripted GUI button; the builder confirms the engine
  passes it, else a second pair of buttons).

### 8.5 The pace

The pace is `ceil(L / 48)` levels a month, at least 1: a quarter of the base a
year, whoever decided the move. New levels, displacement and return don't count
against it. A base of 150 levels moves 4 a month, so it moves from Psyche to
Ceres in about three years (§ 12, answer 4).

### 8.6 What is unchanged

- The near-Earth asteroids are one more place: Mixed, grade 0, room 10 with
  Asteroid Mining.
- Levels past all of the room work at −75% and count as Mixed.
- The AI's and private investors' build gates read room only, as today.
- The property the owner set on 2026-10-25 still holds: a new poor colony adds
  room without lowering what the levels earn. A new site only adds a choice, and
  under the checkbox levels move to it only if it earns more.

### 8.7 The modifiers, in short

`T` as today; `D(g)` on each base building from `sr_ebase_mix_<good>`, removed
and re-added every run; the fourteen unit modifiers (§ 5.3).

### 8.8 Edge cases

- **Races Only**: bases have no room, so there are no sites, no mix and no panel.
  Bases make the basket at the throughput they have.
- **A country with no record** (`sr_eb_placed` unset: a new game, the first base
  in a country's history) places all its levels at once by the rule in force.
  This is not old-save code: 1.15 loads no older save (owner, 2026-11-06), so
  nothing is kept for one.
- **Revolutions**: the counts, targets and checkbox are variables, so the winner
  keeps them. Its modifiers come back from the next refresh.
- **The AI** never sets `sr_eb_manual`.
- **Game rule switched mid-game** (Simple or Full Colonies to Races Only): the
  refresh adds no mix modifiers and removes them from every base. The counts
  wait in their variables for the rule to come back: a rule switched off
  pauses a system, and switched back on resumes it.

## 9. What the player can see

Each reading below answers one of § 2's three questions. Where it sits follows
`gui_style_guide.md`: figures as tables, brief labels with the detail on
hover, the rules on the Help page.

### 9.1 The Bases view (where the levels work, what the base makes)

A fifth view in the Colonies section, beside People, Modules, Autonomy and
Defenses, shown under Simple and Full Colonies with In-Situ Resource
Utilization. Each held colony's box shows its type and grade, its levels, its
profit a level and its output a level. Above the rows are the checkbox, the
base's totals and the near-Earth asteroids' row. A sketch, with 150 Asteroid
Mine levels: all at 16 Psyche, the best site at base prices, until Glass and
Plastics went 50% dear five months ago. The near-Earth asteroids take part like
any site, and here they earn least a level, so they hold none:

```
 People   Modules   Autonomy   Defenses   [Bases]

 [x] Assign for the most profit            150 built, 20 queued / 510 room
 Moving 4 levels a month from 16 Psyche to Ceres, since March 2071:
 Ceres earns 23% more a level at today's prices.

              Struct  Tech   Gold  Cond  Base  Chem  Glass   Profit a week
 Now           52.0k  34.0k  11.8k 20.0k  1.8k  2.4k  4.6k   £1.48m
 If prices
 hold          35.7k  28.1k   5.8k 15.3k  1.6k  8.9k 26.2k   £1.78m

 Near-Earth asteroids   Mixed 0%      0 / 10                 £8,650 a level

 ┌ [icon] 16 Psyche ──────────────────────────── Metallic +30% ┐
 │ 130 / 300   [−] [+]                          £9,594 a level │
 │ Struct 363  Tech 233  Gold 85  Cond 138  Base 12  Chem 9  Glass 8 │
 └──────────────────────────────────────────────────────────────┘
 ┌ [icon] Ceres ──────────────────────────── Carbonaceous +15% ┐
 │ 20 / 200    [−] [+]                         £11,835 a level │
 │ Struct 238  Tech 187  Gold 39  Cond 102  Base 11  Chem 59  Glass 175 │
 └──────────────────────────────────────────────────────────────┘
```

(Goods are icons in game; the words stand in for them here.)

- **The checkbox** (`checkbutton`), a scripted GUI that sets or clears
  `sr_eb_manual`. Its hover is the rule in a sentence: "Each month, up to a
  quarter of our levels a year move from the site that earns least a level to
  the one that earns most, while the gain is worth it."
- **The move line** names the source, the destination, when the move began and
  why, in figures. It also says when nothing moves and why: "Every site loses
  money a level at today's prices: levels stay where they are"; "No site earns
  5% more a level than another"; "Moving toward our assignments: 30 levels to
  go, about 8 months".
- **The totals table**: "Now" is what the base makes from where its levels work
  (`S(g)` × base), with the base's profit a week. With the checkbox on, the
  second row is "If prices hold": the checkbox's own rule (§ 8.3) run to where
  it stops at today's prices, from where the levels are now, with no pace. That
  is a few dozen passes of § 8.2's step 5, run by the refresh and by each click
  for a player's country only. It promises no move the checkbox wouldn't make,
  and its hover says prices respond as the base moves. With it off, the second
  row is "At our assignments", so the player sees what the production would be
  (owner's call 4). Both are computed by the refresh and by every button click,
  into variables, rather than live in the GUI. They are labeled "before other
  modifiers", and the totals hover names the throughput modifiers on top.
- **Each box**: the type's word and the grade (hover: the type's mix and what
  it is, § 6.2); levels working over room, with "→ 50" while the levels there
  are moving toward a target; the − and + buttons; the profit a level, a week at
  today's prices (owner's call 11); and the output a level, seven goods,
  icons first. Output a level is for the method most of our levels run, named
  in the view's hover; the shared basket makes the proportions the same for
  every method, so one method's figures stand for all. Profit a level is the
  checkbox's own figure, which weights the methods by their levels (§ 8.3). A site that doesn't
  serve us this month says why where its levels would be: "Blockaded: 30
  levels working elsewhere until it is freed".
- **Width**: the column is 480. Seven goods of an icon and up to five digits fit
  in about 450. `test_space_race_labels.py` measures the widest, as it
  measures the other views.
- **As built**, to fit the column:
  - dates are years, as the mod shows the month index elsewhere ("since 2071");
  - the move area is up to three short lines (the pace and the year, From and
    To, the gain), since one line doesn't fit 472 with "Near-Earth Asteroids" in
    it;
  - the totals are rows, each a label and the profit a week over a line of the
    seven goods, since a table with a label column doesn't fit;
  - the not-serving line is "Blockaded: 30 working elsewhere until freed", with
    the rule on hover, and only while the site is owed levels;
  - the gain is a percentage of the source's profit, capped at 999%, and the
    profits are compact ("£+9.59K");
  - with the checkbox off, an Unassigned levels row beside the levels rows counts
    built and queued levels less those assigned.

### 9.2 Solar System (choosing a site before holding it)

The line under each site's name shows its slots and its base room and grade
today ("300 (+30%)"). It gains the type's word or icon ("300 (+30%) Metallic"),
whichever fits (`test_space_race_labels.py` measures it). Its hover,
`je_space_race_widget_ss_bases_tt`, is one static key for every site today
(`space_race_widget.gui`), so it becomes a generated key per type that adds the
type's mix. **As built**, six hand-written keys, `je_space_race_widget_ss_bases_tt_<type>`
(no site is Mixed), chosen per site by the generated row's override; the word sits
after the grade in a cell of its own. A player weighing which site to colonize
or seize then sees what it holds before the choice (review point 4).

### 9.3 The Base Room cell

The overview cell keeps "120 +20 / 400" and its red. "Next at" names where the
next level goes instead of a grade, "next: Ceres", and its hover gives that
site's type, grade and profit a level (review point 11). With all the room in
use it reads −75%, as today. **As built**, the line names the site alone ("Ceres"):
the cell's column holds about 16 characters, and the longest name, Valles
Marineris, is 16; the hover says what it is.

### 9.4 When levels start to move (why it last moved)

- **A notice** (`post_notification`, as Banking's and the decolonization wars'
  notices do) when the checkbox starts moving levels toward a different type:
  "Our Extraplanetary Bases are moving from 16 Psyche to Ceres: Glass and
  Plastics earn more there at today's prices." Once per new pair of types, at
  most once a year, so a base settling at the margin doesn't repeat it, and
  only once the move has carried at least 5% of the base's levels: one level of
  a thousand needs no notice (owner, 2026-11-21). The threshold counts levels
  moved, because a move at the margin can't know its size in advance. No
  notice for the player's own moves, or for displacement, which the
  blockade's own notices cover.
- **The move line** of § 9.1 stays as the record while the move runs; after it
  ends, "Last move: 16 Psyche to Ceres, March 2071 to May 2074".
- **As built**, the notice's 5% counts the levels moved between the pair of
  types, so a move that passes from one site of a type to another of the same
  type keeps its count; the record still follows the sites. The last move reads
  "Last move: 2071 to 2074", then "From 16 Psyche to Ceres". Switching the
  checkbox either way ends the running move.

### 9.5 The building and its modifiers

The fourteen modifiers are named for what they are, Extraplanetary Base Ground,
and their descriptions say they apply on top of Extraplanetary Base Room, which
carries the grade. A base at one site shows its grade as throughput and its
type's mix on the goods (§ 5.2), the same two figures the Bases view and the
Solar System view give.

### 9.6 Concepts and the Help page

- **Base Grade** (`concept_sr_base_grade_desc`), rewritten: how much a site
  yields overall, the throughput its levels work at, which scales inputs too.
  Its meaning doesn't change: because every mix averages to zero, the grade is
  still the site's yield and profit at base prices.
- **Ground Type**, a new concept: which goods a site's ground holds, the seven
  types in a line each, and the rule that among sites of one type the better
  grade wins.
- **The Help page** (How Solar Colonization Works) gains the § 6.2 table and the
  checkbox's rule. The 40 per-site hovers (`je_space_race_widget_bases_tt_<site>`)
  stay hand-written, each splicing its type's description key, and a test keeps
  each naming its own site's type. That needs no new generated loc category in
  `organize_loc.py`.

### 9.7 The player guide

`16-space.md` § Extraplanetary Base room keeps its grade table and gains the
seven types as a table with each one's sites, the patterns of § 6.4 in a few
sentences, and a subsection of its own on the Bases view and the checkbox,
since it is a system the player works through. `02-timeline.md` gives Regolith
Processing's goods. The basket's changes go in the build PR's description, for
the release notes (§ 7). The PDF is rebuilt with the chapters.

## 10. What changes (the build)

**One implementation PR, built in stages** (owner's call 13): the release waits
for all of it, and one PR writes the player guide and the PDF once rather than
twice and needs no interim panel on today's order. The stages are commits, in
this order, each with its tests. The plan is
`docs/superpowers/plans/2026-11-21-extraplanetary-base-ground-types.md`:

1. **The types, the sites and the basket.** `gen_solar_sites.py`: the seven
   types and each site's, and the normalization.
   `extra_pms.txt`: the basket (§ 7); the cost comments are rewritten by
   `pm_costs` on reload, and the note above `pm_space_mine` is rewritten by hand.
   Tests: every type's mean is zero; every derived grade is the site's; for
   every type and method, a level's profit at grade 0 and base prices is the
   method's base profit to within 0.1%; Regolith Processing's £1,600 and 2.0;
   the Deep-Sea test's second exception. `ExtraplanetaryBaseMix`'s Conductive
   floor and four-times rule still pass unchanged.
2. **The two layers on today's order.** `sr_ebase_refresh` fills by grade into
   the `at` counts, computes `T` and the seven `D(g)` and applies them per
   building (§ 5.3). The display entry for `goods_output_lead_mult` (the other
   six exist), the fourteen unit modifiers, their loc and Nation tab lines. Self-check
   `TE_SELF_CHECK ebase_mix`: a base's building carries the `D(g)` it was given.
   Script can't read a building's output of a good, so § 5.2's product form is a
   play-test item: one base's output tooltip at one site reads base ×
   (1 + its throughput) × (1 + `D`). Play-test list:
   `docs/testing/solar-colonies-playtest.md`.
3. **Where the levels work.** The variables, the month's six steps (§ 8.2), the
   checkbox's rule and its prices (§ 8.3), the pace, displacement and return.
   Generated per-place script for the passes. Tests on the generated structure,
   and a Python model of the month (moves, pace, margin, displacement) run over
   a few price paths, as `test_gw_geoengineering.py` runs its step in Python:
   a glut stops the moves inside the margin, with no back-and-forth.
4. **The panel.** The Bases view, the scripted GUIs (checkbox, − and +), the
   Solar System word, the Base Room cell, the notice, the concepts and the Help
   page.
5. **Docs.** `space_race.md`, `production_methods.md`, the player guide and its
   PDF, the play-test items: the acceptance test of § 2, a large
   base under a glut watched for a back-and-forth, a blockade and its return.

If review load argues for two PRs instead, stages 1 and 2 are the first and 3
to 5 the second. The first then ships no player guide change beyond the basket
and the types, and the second writes the rest.

## 11. Not in scope

- Price smoothing, a yearly ranking or a plan margin (§ 8.3 replaces them).
- A separate priority per colony (the first draft's option B).
- Any change to room, to the grades, or to the build gates.
- The Resort Colony's new home (§ 7), another session's work.

## 12. The owner's answers to the calls (2026-11-21)

1. **The basket** (§ 7): as drafted. Glass and Plastics are 7.5% of output value,
   taken from Tech-Critical Metals (−17% on the later methods). Conductive Metals
   keep the tenth of sales set on 2026-11-15. Regolith Processing's Structural
   Metals fall 36%, and its outputs have two decimals.
2. **The seven types and their mixes** (§ 6.2): as drafted. Icy stays a hedge,
   the middle of the road, never the best for one good alone.
3. **The sites** (§ 6.3): as drafted. Mare Imbrium is Rocky (its `kreep`
   specialization keeps the flavor). The Venus Cloud Habitat is Sulfurous
   (Glass and Plastics +13% there). Utopia and Arcadia Planitia are Icy, and the
   other three Mars sites Rocky. Enceladus is Carbonaceous, Mercury Rocky, and
   the two lunar poles and Eris Icy.
4. **The pace and the margin** (§ 8.3, § 8.5): a quarter of the base a year, and
   5% of the yardstick.
5. **When every site loses money a level, nothing moves** (§ 8.3). The owner
   suggested maximizing revenue in this case, or else nothing moving. § 8.3
   gives the reason for holding: more revenue raises the demand for the dear
   input that causes the loss.
6. **The notice** (§ 9.4): once per new pair of types, at most once a year, and
   only once the move has carried 5% of the base's levels. The owner asked for
   a threshold on move size, and the 5% is this document's.
7. **The Resort Colony** leaves this building (§ 7). The owner is considering a
   building type of its own, as another session's work.
8. **One implementation PR in five stages** (§ 10).

## Appendix: the review's points and where they are answered

| Review point | Answer |
|---|---|
| 1. The site's score and the building's modifier differ | § 5.2: for a base on one type the building shows the type's mix and the grade as throughput; § 9.5 |
| 2. The base's mix is shown nowhere | § 9.1, the totals table |
| 3. Nothing shows which sites the levels work | § 9.1, levels a box |
| 4. The mix is missing where the player decides | § 9.2, the type in Solar System; § 9.6, the Help table |
| 5. "Base Grade" stops meaning what it says | § 9.6: with mixes of mean zero its meaning is unchanged |
| 6. Saves change output, only one change named | § 7, the changes by method; § 9.7 |
| 7. The ranking's inputs are invisible | No ranking. § 8.3's rule is one line, on the checkbox's hover; § 9.1's move line gives the figures |
| 8. A move needs a notice | § 9.4 |
| 9. No way to say no | The checkbox (owner's call 5) |
| 10. When every site loses money | § 8.3, nothing moves, and § 9.1 says so |
| 11. "next: Titan, −15%" shows the wrong figure | § 9.3 |
| Stale: seven goods, outputs, the Base Metals modifier, the Deep-Sea test, the index row | Rebased onto `main`: § 7, keeping Conductive Metals' 2026-11-15 floor; § 5.3 (the modifier exists, only its display entry is missing); § 7; the index row merged without conflict |
| Smaller: § 5.2's mixed column; precision | § 6.4 gives each figure a column; § 5.3, whole percents |
