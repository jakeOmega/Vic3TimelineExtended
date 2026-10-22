# Demographic effects that matter: Wealth Concentration, inequality, where people live, sex balance and the youth bulge — design

## Context

The census's consequence modifiers and Wealth Concentration's five modifiers were built small on purpose: the master
spec's design rule 5 says effects are "deviations from a stated reference, and capped", and its §7 sizes most of them
"small" (`docs/superpowers/specs/2026-10-08-demographics-design.md`). Seen in game, they don't matter enough (owner,
2026-10-22). A review of the modifiers against the engine's catalogue (`docs/engine/modifiers_summary.txt`) and
vanilla's own sizes (`vanilla_parsed/common/*.json`) found four reasons:

1. **They rarely reach full strength.** Each ramps from a neutral point to the far end of its scale. Wealth
   Concentration's modifiers are full at a score of 100 or 0 (`te_inheritance_values.txt`), More Men at 150 men per 100
   women, the urban pattern at 60% primacy. From the target's terms, most 1836 states should sit at about 55–70 (a
   Customary-inheritance country: 50, plus Serfdom's +15 × an agrarian share near 0.8, plus 0 to +10 from the economic
   laws), so Concentrated Property runs at 10–40% of its size and moves radicals and qualifications by 1–4%. Only
   Primogeniture or Forced Heirship countries feel it. The sex-balance effects reach 0.1–0.6% of states since the
   migrant booking (`docs/systems/mod_systems.md` § Phase 2 step 4). These figures come from the formulas, not saves:
   Phase 0 measures them.
2. **Full strength is small against vanilla.** The modifiers top out at 10–20%. A vanilla law moves the same fields by
   25–50%: Monarchy +25% Aristocrats' clout, the Guild System −20% qualifications, Laissez-Faire +25% Capitalists'
   investment-pool efficiency.
3. **Nearly every downside is one of two fields.** Concentrated Property, Inequality, the Youth Bulge and More Men all
   raise `state_radicals_from_political_movements_mult`; Provincial Neglect, Metropolis and the Youth Bulge raise
   `state_turmoil_effects_mult`. Both bite only once a movement or turmoil exists, and a player can't tell which
   condition is doing what.
4. **The good side is mostly empty.** A Balanced or Dispersed urban pattern, Several Cities and low inequality do
   nothing; Dispersed Property gives Farmers' and Shopkeepers' investment pool +10% and nothing else.

Only Wealth Concentration acts under every Demographics rule setting; the census's effects act only under Full.

**What Wealth Concentration measures** (owner, 2026-10-22, restating the master spec §4.2): how property is held
*within* the owning pops. Vanilla already models who owns a building: a farm owned by its farmers (self-owned) or by a
distant aristocrat (a Manor House) or capitalist (a Financial District). The score is how concentrated that ownership
is: one Rockefeller family holding half of all farms, or hundreds of small firms. Its effects follow from that reading,
not from which pop type holds the property (§ Wealth Concentration below).

## Decisions (owner, 2026-10-22)

| Question | Decision |
|---|---|
| Design rule 5 | **Revised**: a strong condition is worth about one vanilla law on its main effect. The census's own model terms (births, deaths, the workforce term) are not effect sizes and keep their rules |
| Where full strength sits | **At the historical case, as a reference size, not a ceiling.** Going past it still counts (§ The curve) |
| Wealth Concentration's upper end | **Straight line**, no kink: 1.67× at a score of 100 |
| Wealth Concentration's lower end | **The kink**: 1.17× at 10, 1.33× at 0 |
| A national suffrage line for Fewer Men | **Dropped**: the women's rights movement already presses for the laws it wants (§ Sex balance) |
| The dispersed side | **Steadier, not slower** (second round): concentrated property grows faster but crashes more often, dispersed property grows slower but steadier. Dispersed Property loses the owners' efficiency cut; the national pair carries bubble pressure, +0.3 a month at 1× on Great Fortunes and −0.3 on Dispersed Wealth; education access becomes ±0.10 (§ Wealth Concentration) |
| Wealth Concentration under every rule | **The full increase.** If it proves a problem, it moves behind the rule |
| Wealth Concentration's neutral point | **50**, so 1836 starts fairly concentrated and the 20th century's levelling shows |
| One effect per condition | **A default**, kept only where it doesn't cost realism or fun. Land Hunger and the Youth Bulge keep a radicals line |
| Political strength from wealth | **Adopted** on Concentrated Property |
| Inequality's extreme | **A second, steeper slope above a Gini of 0.70**, liked in principle; its size waits on Phase 0 |
| Metropolitan share's cap | **Lifted**: past 15%, about 20% on its main line |
| Phases | **1 and 2 build together**, in a later session |

Every size here is a proposal until Phase 0 and the observer run; the questions still open are listed at the end.

## Principles

1. **A strong condition is worth one vanilla law** on its main effect.
2. **The reference point is a size, not a ceiling** (§ The curve).
3. **Each condition has an effect of its own** where realism allows, so the player can tell them apart:

   | Condition | Its effect |
   |---|---|
   | Wealth Concentration | political capture, capital formation against financial stability, social mobility and schooling |
   | Land Hunger | the Land Reform movement, emigration and rural revolt |
   | Inequality | the Socialist and Labor movements, on top of its radicals |
   | Youth Bulge | general unrest: radicals and turmoil |
   | More Men | turmoil and radicals |
   | Fewer Men | the women's rights movement (which presses for Women's Suffrage itself) |
   | Primate City and Provincial Neglect | big-city growth against regional resentment |
   | Metropolis and Dispersed Towns | infrastructure and agglomeration |

4. **Both poles carry an upside and a cost**, as §5.1 of the master spec already says of the urban pattern ("a choice,
   not a penalty").
5. **The levers already exist**: the inheritance and land laws, taxes, Planned Capital, Settlement Authorities, Family
   Policy and Internal Resettlement. Bigger effects make them worth using; phases 1 and 2 add no buttons.

## The curve

A straight line from the neutral point to the reference point (1×), then half that slope beyond it until the scale
ends, with a hard limit of 2× only where a scale has no natural end. Every point counts and the last ones count a
little less, which matches the owner's note that the real marginal effect is weaker at the extreme. Wealth
Concentration's upper end is the exception: a straight line to 100 (owner).

In script, for a ramp `x` that reads 1 at the reference: `min(x, 1) + max(x − 1, 0) / 2`, clamped at 0 and, where
needed, at 2. One script value per modifier, so each keeps its one refresh site.

| Condition | Neutral | Reference (1×) | Beyond |
|---|---|---|---|
| Wealth Concentration, high | 50 | 80 | straight: 90 → 1.33×, 100 → 1.67× |
| Wealth Concentration, low | 50 | 20 | 10 → 1.17×, 0 → 1.33× (owner) |
| Primacy (largest city's share of urban people) | 25% | 50% | 60% → 1.2×, 80% → 1.6×, 100% → 2× (seen at 60% in game, owner) |
| Metropolitan share, Metropolis side | 40 | 60 | 80 → 1.5×, 95 (the target's ceiling) → 1.88× |
| Metropolitan share, Dispersed side | 20 | 5 (the target's floor) | none |
| More Men (men per 100 women, 20–59) | 110 | 130 | 150 → 1.5×, 170 or more → 2× |
| Fewer Men | 90 | 80 | 70 → 1.5×, 60 or fewer → 2× |
| Youth Bulge | 18% aged 20–29; no unemployment | 24% and 20% unemployment (as now) | each factor at half slope past 1; the product at most 2× |
| Inequality | Gini 0.45 | 0.65 | straight, no cap (as now), steeper above 0.70 (§ Inequality) |

**The census's model terms stay on 0–1.** The sex balance's births term ("Few men to marry", `te_demog_tfr_sex`) and
women's-rate term (`te_demog_sex_women_shown`), and the metropolis's fertility scale (`te_demog_mt_fertility_scale`),
read the same ramps today. They describe the population, not an effect size, so they keep their current clamp: the
extended curve is a new script value read only by `add_modifier`.

Options considered: a straight line on every scale (primacy would run to 3×, More Men past 4×); a smooth saturating
curve (no kink, but hard to state in a tooltip); a flat ceiling at the reference (the first draft: holding a condition
just past the reference costs nothing more, owner rejected).

## Wealth Concentration (every rule setting)

| Modifier | Now, at full strength | Proposed, at the reference (1×) |
|---|---|---|
| Strength | full at 100 or 0 | § The curve |
| Great Fortunes (country) | Aristocrats and Capitalists clout +20% | +20%, now reached at 80; +33% at 100; **bubble pressure +0.3 a month** (+0.5 at 100) |
| Dispersed Wealth (country) | Aristocrats clout −20% | Aristocrats and Capitalists clout −20%; **bubble pressure −0.3 a month** (−0.4 at 0) |
| Concentrated Property (state) | Aristocrats' and Capitalists' investment-pool efficiency +10%, radicals +10%, qualifications −10%, education access −0.05 | efficiency +20%, **political strength from wealth +20%**, qualifications −20%, **education access −0.10**; the radicals line moves to Land Hunger |
| Dispersed Property (state) | Farmers' and Shopkeepers' investment-pool efficiency +10% | political strength from wealth −10%, qualifications +10%, **education access +0.10**, radicals −10%; no investment line |
| Land Hunger (state, farm states) | migration quota +20% | quota +30%, **Land Reform movement support +25%**, radicals +10% |

- **Political capture.** `state_political_strength_from_wealth_mult` multiplies the part of every pop's clout that
  comes from its wealth, so where property is concentrated the rich gain most (vanilla: Political Banquets and the
  Zaibatsu Oligarchy +15%, Low Electoral Confidence +50%). Great Fortunes is not raised, since capture now has a second,
  local line. Where fortunes are many and small, the same wealth buys less influence: no single holder can fund a party
  or a newspaper, and many small owners struggle to act together, hence −10% on the dispersed side (half, since
  dispersal spreads wealth's voice rather than removing it).
- **Capital formation.** Great fortunes save a larger share of their income than small holders do, so concentration
  speeds the investment pool. Efficiency, not contribution: both scale the same flow (+20% efficiency is about +0.06
  on the Capitalists' 0.30 contribution), and efficiency reads as a plain percentage. Dispersal does not slow it
  (owner, second round): small owners save too (the French peasant's stocking, Japan's postal savings), and an
  efficiency cut on the dispersed side made the gap between the poles 46 points on a field that compounds (+33% at
  100, −13% at 0).
- **Financial stability** (owner, second round). The rich's extra saving does not all become investment: it is lent
  to everyone else and bids up assets. Kumhof, Rancière and Winant (2015) find sharp rises in top incomes before both
  1929 and 2008; Mian, Straub and Sufi find the saving glut of the rich financed debt more than investment. And many
  owners deciding separately don't all pile into one bond issue, as Barings did with Argentina's in 1890 (the owner's
  "decisions made by a larger base of people"). So the national pair carries bubble pressure: Great Fortunes +0.3 a
  month at 1× (+0.5 at 100), Dispersed Wealth −0.3 (−0.4 at 0). That is a Cautious ruler's size (−0.3; Reckless +0.6,
  fiat money +0.2): over a five-year boom, 18 points against the 65 at which a state's chance of a financial panic
  doubles. It is a country field, so it sits on the national pair, whose refresh (`te_demog_wc_national`) already
  exists, never on the per-state pair. It acts only once a country's banking cycle runs (`te_banking_cycle_running`:
  a stock exchange and a level-5 Urban Center) and the banking rule is on; before that, a dispersed country such as
  France (Forced Heirship, about 25–35 in 1836) has only the schooling and mobility lines. The result is concentrated
  property growing faster and crashing more often, dispersed property growing slower and steadier. The banking
  dashboard's next-month range reads the modifier total (`banking_disp_bubble_change_lo`/`_hi`), so the new source
  shows there with no GUI work.
- **Mobility and schooling.** Concentrated property shortens the ladder (−20% qualifications, the Guild System's
  figure); dispersed property opens it (+10%). Where land was concentrated, landowners held back public schooling
  (Galor, Moav and Vollrath 2009 on the US states; Engerman and Sokoloff on the Americas), so education access is
  −0.10 on the concentrated side and +0.10 on the dispersed side, about one level of Public Schools (+0.125 a level).
  This is the dispersed side's slow-compounding route: literacy into qualifications.
- **Stability.** A wide propertied middle resists revolutionary movements (radicals −10% on the dispersed side).
- **Land hunger.** Great estates left the young no land of their own: emigration (southern Italy) and rural revolt
  (Andalusia, Russia 1905, Mexico 1910). The base game creates the Land Reform movement only after Enclosure, in a
  country over 25% Peasants that has enacted neither Peasant Proprietorship nor Collectivized Agriculture, so the
  support shows where history put it.
- **Why the dispersed side changed** (owner's note, 2026-10-22). The first draft gave Dispersed Wealth Farmers' and
  Shopkeepers' clout +15%, on the reading that they hold dispersed property. But vanilla's building ownership already
  decides whether farmers own their farms; the score measures concentration within the owners. A pop-type bonus would
  restate vanilla's ownership. The dispersed side now acts on the same owning pops as the concentrated side, in the other
  direction. This also drops the draft's open question of a cooperative split (Laborers and Machinists as owners under
  Cooperative Ownership): vanilla's worker ownership handles who owns.
- **The arc.** With the reference at 80, a serf-estate country starts 1836 at about half strength and falls as reforms,
  wars, taxes and crises level it.

Options considered: raise the values but keep the curve (only Primogeniture countries feel it); centre the curve on the
measured 1836 median, so 1836 starts neutral (owner: keep 50); tax waste on Concentrated Property, great fortunes
avoiding tax (left out: the tax code already prices wealth); Farmers' and Shopkeepers' clout on Dispersed Wealth
(above); contribution in place of efficiency. For the dispersed side (second round): owners' efficiency −10% (the
first proposal; dropped above); Banking Crash Likelihood in place of bubble pressure (laws use ±10–50%; bubble pressure
is the owner's idea and shows on the dashboard as it builds); the workforce's chance to own new levels
(`building_self_investment_chance_add`: it changes who owns, which the owner's note leaves to vanilla); resilience to a
state's financial panic (`state_harvest_condition_financial_panic_impact_mult`: it reaches only financial-centre states,
a weaker copy of the bubble line); tax capacity (the tax code already prices wealth); a home-market demand bonus (the
engine already sets demand from pops' wealth).

## Inequality (Gini, Full only)

The game's late Ginis run above history's (§4.1): the 2054 save's median shown Gini is 0.64, with 627 of 755 states
above 0.45 and 360 at 0.65 or more, so the radicals line already gives about +9.5% nearly everywhere late.

- **Radicals:** the slope stays +10% per 0.2 above 0.45 up to 0.70. Above 0.70 it doubles, to +10% per 0.1 (the owner
  likes a steeper extreme; the size waits on Phase 0's count of late states above 0.70). One multiplier,
  `(g − 0.45) / 0.20 + max(g − 0.70, 0) / 0.20`: 1.0 at 0.65, 1.25 at 0.70, 2.25 at 0.80.
- **Socialist and Labor movement support, +10% each at 1×**, on the same modifier and multiplier. The movements need
  their technologies, so the early game is unchanged, and inequality then pushes toward welfare laws as well as unrest.
- Not steeper below 0.70: that would turn a choice into a charge every late state pays, on Ginis that already
  overshoot.

Options considered: a steeper slope everywhere; an upside for low inequality (few states get there); a higher
lower-strata standard-of-living expectation (`state_lower_strata_expected_sol_add`, very strong: vanilla's high tax is
+1.5); split the movement lines into their own modifier so the steep part touches only radicals (if Phase 0 shows them
too strong at the top).

## The urban pattern (national primacy, Full only)

| Modifier | Now, at full strength (60% primacy) | Proposed, at the reference (50%) |
|---|---|---|
| Primate City | Urban Center throughput +10%, migration pull +15% | throughput +20%, pull +25%, **University throughput +10%** |
| Provincial Neglect | pull −10%, turmoil effects +10% | pull −15%, turmoil effects +15%, **Cultural Minority movement support +15%** |

- University throughput: talent and ideas gather in the great city (Paris, London, Tokyo). Vanilla's monument rewards
  give Urban Center throughput +25%, the yardstick for +20%.
- Cultural Minority support moves only a province with an identity of its own (Catalonia, Scotland); in a province of
  the primary culture it does nothing, which is the realistic shape of regional resentment.
- Values in `te_demog_place_values.txt` (`te_demog_k_up_floor` 0.25 stays, `te_demog_k_up_span` 0.35 → 0.25, then the
  curve).

Options considered: an upside for a Balanced pattern; raise the sizes only; **Primate City's upside fading with
development** (open, below).

## The metropolitan share (per state, Full only)

| Modifier | Now, at full strength | Proposed, at the reference |
|---|---|---|
| Metropolis (share 60) | crowding density −10%, infrastructure from population +10%, Urban Center throughput +5%, turmoil effects +5% | crowding −10% (unchanged: it feeds the target's loop), **infrastructure from population +20%**, throughput +10%, turmoil +10% |
| Dispersed Towns (share 5) | infrastructure from population −10% | −20% |

**Crowding keeps its 0–1 strength.** It raises the state's Migration Crowding, which lowers the share's target
(`te_demog_mt_t_crowding`): a model term like the fertility scale, which reads the same `te_demog_mt_e_pos`. So it moves
off `te_demog_mt_metropolis` into a modifier of its own, applied beside it at the same refresh
(`te_demog_mt_state_refresh`) with the 0–1 multiplier, and the share's balance points don't move. The other three fields
stay on `te_demog_mt_metropolis` and take the extended curve. The builder names the new modifier and decides whether
it shows; `test_demographics_metro.py` pins both.

The stack to watch is the primate metropolis: at 60% primacy and a share of 80, Primate City (+24%) and Metropolis
(+15%) give about +39% Urban Center throughput, against vanilla's largest single bonus of +33% (`modifier_urban_centers`).
Acceptable for the most extreme city in the game; Phase 0 checks how many states it reaches. Values in
`demographics_params.MT_EFFECTS` (owner's 10% cap of 2026-10-19 lifted).

## Sex balance (Full only)

| Modifier | Now | Proposed, at the reference |
|---|---|---|
| Fewer Men (state; 0 at 90, 1× at 80) | women's rights movement support +10% | **+25%** |
| More Men (state; 0 at 110, 1× at 130, was 150) | radicals +10% | radicals +15%, **turmoil effects +15%** |

- **No national suffrage line** (owner, 2026-10-22). The first draft added a country modifier, Women's Suffrage
  enactment success +10%, for the suffrage wave after the First World War. Dropped: the women's rights movement
  already raises the enactment chance of the laws it wants once its activism is high enough, so the movement support
  above reaches Women's Suffrage on its own and a second line would count the same push twice. (Its field,
  `country_enactment_success_chance_law_womens_suffrage_add`, is registered by neither vanilla nor the mod either.)
- Turmoil stands in for the crime and violence of a surplus of young men (Hudson and den Boer, *Bare Branches*); the
  engine has no crime.
- No conscription line: the census's conscription term already raises conscripts where young men are many.
- The effects stay rare (after great wars, under Birth Limit, on Internal Resettlement's frontiers), which is right.

Options considered: loosen the migrant booking so frontiers read 130 or more again (not recommended: the booking exists
to remove artefacts).

## The youth bulge (Full only)

Radicals +15% → **+25%**, turmoil effects +10% → **+15%** at y = 1 (`demographics_params.YOUTH_RADICALS`,
`YOUTH_TURMOIL`). With the other conditions moved to effects of their own, this becomes the main demographic source of
general unrest; the youth-bulge literature (Urdal 2006) puts it among the strongest demographic predictors of conflict.

## Unchanged

- **The longevity gap's politics**: late game only, and already priced in approval.
- **The conscription term**: no ceiling since 2026-10-16.

## Phase 0: measure (before phases 1 and 2)

The plan's distributions are estimates from the formulas; no save is in the repository. The owner runs the readouts on
plain-text saves at 1836, about 1880, about 1936 and a late year:

- `demographics_harness.py wc SAVE` already prints each country's figure, terms and multipliers and its states' range.
  Add a histogram of state scores and the share of people at each strength under the current and the proposed curves.
- `gini SAVE`: add the count of states (and people) above 0.70.
- New `effects SAVE` command: for each modifier here, the states and people at each strength, current against
  proposed, from the save's `te_dg_*` variables (`te_dg_wc`, `te_dg_up_s` and primacy, `te_dg_mt`,
  `te_dg_sex_balance`, `te_dg_yb`, `te_dg_gini`); the radicals and turmoil stack per state (the worst ten); and the
  primate metropolis's Urban Center throughput stack. It can be built and unit-tested in a container with synthetic
  variables before any save is read.
- Late primate countries: their largest city's Migration Crowding (`migration_crowding_mult_applied`), which decides
  whether Primate City's fade is needed.
- The bubble line in the banking simulator: `banking_cycle_sim.py` reads bubble pressure only from laws, so add a flat
  monthly term (`--extra-bubble X`) and compare crashes a century at 0, ±0.3 and +0.5, with no tools and with a
  player's points. No save needed.

Phase 0 sets the steep Gini slope's size and the bubble line's, and settles the fade.

**Phase 0 doesn't hold up the build** (my call, 2026-10-22, from the owner's standing rule that owner-run checks
don't gate work). The tools come first, since they need no save. Then the build goes ahead at the starting sizes in
this document, and the save readouts and the simulator table go into the PR for the owner. A size moves before merge
only when its test fails:

- **The bubble line:** keep ±0.3 if, in the simulator's untooled market arm, a score-100 country crashes roughly 10–30%
  more often a century than a neutral one, and a score-0 country roughly 10–25% less. Below that the line is lost in
  the noise, and above it, it outweighs the efficiency it is meant to balance. Scale the 0.3 to land inside the band.
- **The steep Gini slope:** keep doubling unless the readout puts more than about a third of late states above 0.70.
  Then the steep part is a charge nearly every late state pays, so halve the extra slope (+10% per 0.2 becomes +5%).
  The owner reads the count, since the saves are theirs.
- **Primate City's fade:** built only if the crowding read calls for it (Phase 3).

The simulator's term is flat (`--extra-bubble X`, one value per run at 0, ±0.3 and +0.5), not the score moving with
the cycle. The loop is small: a Frenzy adds 5 to every state's score (`te_demog_wc_boom_check`) and a crash takes 5 off
(`banking_cycle_effects.txt`). The line's slope is 0.01 a month per point (0.3 over the 30 points from 50 to 80), so a
Frenzy adds 0.05 a month, a sixth of the line at 1×.

## Phases 1 and 2: the build (together)

Re-anchor the curves, resize the existing fields and add the new ones in one PR, or two if Wealth Concentration goes
first, since it reaches every game.

- **Sizes and curves:** `common/static_modifiers/te_inheritance_modifiers.txt` and `te_inheritance_values.txt` (Wealth
  Concentration); `te_demog_inequality_modifiers.txt` and the refresh in `te_demog_wealth_effects.txt`;
  `te_demog_place_modifiers.txt` and `te_demog_place_values.txt`; `scripts/analysis/demographics_params.py`
  (`MT_EFFECTS`, `YOUTH_*`, `SEX_*`), then the generator for the `te_demog_k_*` constants, `te_demog_metro_modifiers.txt`,
  `te_demog_consequence_modifiers.txt` and `te_demog_consequence_values.txt` (new effect-strength values beside the
  model's 0–1 ramps).
- **Builder's notes:** `te_demog_k_up_span` 0.35 → 0.25 moves the primacy strength the Planned Capital AI reads from
  `te_dg_up_s`; hold its threshold where it is with a constant. `state_pop_support_movement_land_reform_mult` has only
  a placeholder description in the engine catalogue, so check its label in game and add mod localization if it shows
  raw.
- **Tests that pin sizes:** `test_demographics_place.py`, `test_demographics_metro.py`, `test_demographics_registry.py`
  (`TestInheritanceBalance`, and the youth and sex sizes), `test_demographics_wc_shocks.py` (the Inequality modifier's
  refresh, body and description), `test_hidden_state_modifiers.py`; the Python twins
  (`demographics_metro.py`, `demographics_harness.py consequences`) follow the script.
- **Localization:** the modifiers' descriptions and every hover that states a size (the Urban Pattern rows'
  `te_demog_up_shown_*`, the settlement tooltip, the sex balance and youth hovers, the Wealth Concentration concept and
  law group text); grep the loc for the old figures.
- **Player guide:** `06-politics.md` (the Wealth Concentration table), `08-states.md` (the census modifiers, the urban
  pattern and settlement), `04-banking.md` (the sentence listing what pushes bubble pressure: Fiat Money and Digital
  Currency's +0.2, now Great Fortunes and Dispersed Wealth too), rebuilt PDF.
- **Nation tab:** the national pair's new field needs no row: `gen_nation_tab.py`'s `NOT_A_ROW` already sends
  `country_bubble_pressure_monthly_add` to the Banking tab.
- **Docs:** `docs/systems/mod_systems.md` (§ Inheritance, § Demographics' Wealth Concentration, Inequality, urban
  pattern, metropolitan share and phase 2 step 4 subsections); the master spec's design rule 5 and §7 table, pointing
  here.
- **Play-test list** (`docs/testing/demographics-playtest.md`): the tooltips show the new figures; a score past 80
  still moves the modifiers; Land Reform support appears in a land-hungry state with the movement present; Fewer Men's
  women's rights support after a war that kills a twentieth of the men; an observer run to about 1950 for AI stability and
  law paths (AI Britain's reforms will be slower under more aristocratic clout, which is historically right until 1911).
- **Self-checks:** none expected. Every field is a registered type (vanilla's, or the mod's own bubble pressure, which
  the banking cycle's script reads) on a state or country static modifier with a multiplier, a pattern the mod already
  relies on.

## Phase 3: later

- **Urban share as an amplifier**: Inequality and the Youth Bulge scaled by (0.5 + the state's urban share), since
  movements organize in cities (Paris 1848, Petrograd 1917, Cairo 2011). Nothing reads a state's urban share today
  except the fertility term and the metropolitan target. A stand-alone urban modifier (political strength, literacy
  growth) was considered and dropped: it would restate vanilla's Urban Centers.
- **A Demographic Dividend while the young have work**: investment-pool efficiency +10%, life-cycle saving (the master
  spec §7's "optional, later"). Not throughput: the workforce term already supplies the labour. Today only the
  once-a-generation event gives the dividend.
- **Threshold events**: The Gilded Age (the national figure at 75 or more under Laissez-Faire), The Land Question (a
  land-hungry state with the Land Reform movement present), The Provinces Rise (Provincial Neglect with turmoil).
- **Primate City's fade**, if Phase 0 calls for it.

## Risks

- **Reach.** Wealth Concentration changes reach every game; the census's reach only Full games. Wealth Concentration
  can go in its own PR, with an observer run.
- **Stacking.** The worst radicals stack in one state grows (the Youth Bulge at 2× is +50%, Inequality at 0.80 +22.5%,
  More Men at 2× +30%, Land Hunger +10% × its farm share). The conditions rarely coincide; Phase 0 measures how often.
  A combined per-state cap, one multiplier over all of them, is the fallback.
- **Self-reinforcement.** More owners' investment, more capitalists, a higher Gini, a higher Wealth Concentration
  target. The 3% yearly drift and the inequality term's ±15 cap bound it. The bubble line adds a second, small loop:
  more bubble, more Frenzies, +5 to the score each, more bubble (+0.05 a month per Frenzy), undone by the −5 a crash
  takes (§ Phase 0).
- **The top of the scale.** Concentrated Property at a score of 100 gives qualifications −33% and investment +33%;
  reaching 100 takes Primogeniture with Perpetual Dynastic Trusts, Laissez-Faire and a high Gini.
- **AI.** The AI steers none of these; the observer run checks stability and law paths. Bubble pressure reaches the AI
  through its banking tools, whose weights already answer the bubble whatever pushes it.

## Open decisions

Settled 2026-10-22, second round: the lower end's kink, and the dispersed side (§ Decisions). Left to Phase 0:

1. The steep Gini slope's size: doubling above 0.70 is the starting point.
2. The bubble line's size: ±0.3 a month at 1× is the starting point; the simulator sets it.
3. Primate City's fade with development: settled by the crowding read.
4. The sizes as a whole are proposals until Phase 0 and the observer run.
