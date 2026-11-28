# Ownership concentration: a fixed partnership in Financial Districts and company headquarters: scope

Drafted 2026-11-28 from the owner's request. This is a scoping document: what
to build, the engine facts it rests on, and the calls the owner has to make.
It is not yet a design, and it has no implementation plan.

**Status (2026-11-28):** built the same day, on the owner's answers below. The sizes are
provisional until the save measurements (§ 9, M1 to M3); the play-test list is
`docs/testing/ownership-concentration-playtest.md`, and the systems docs are
`docs/systems/mod_systems/production_methods.md` § Ownership buildings and
`demographics.md` § Dynastic Wealth per state.

## Decisions (owner, 2026-11-28)

- Call 1: the aristocrats of aristocrat-owned headquarters split too ("yes").
- Call 2: the sizes are settled on saves ("ok"). Built at the starting shape, 6T once a
  building and 0.4T a level (break-even at level 10).
- Call 5: Scale of Fortunes is built ("sure").
- Call 8: the tier gates are fixed in the same build ("sure").
- The other calls took the recommendations: Manor Houses unchanged (4), the term measured
  from owned assets (6), regional headquarters with their own partnership (7), no
  migration for old saves (9). Call 3 took the proportional tiers for the Financial
  District; the headquarters' own tier copies keep their category's owners and automate
  only the back office, since employment figures are whole numbers and 60%, 40% and 20%
  of a 10-capitalist category's owners are not.
- Built differently from § 5.2: the owners are the buildings' capitalist and aristocrat
  positions (their `modifier:` reads), not the walk's employed pops, and the centre r₀ is
  the world's figure measured in the game once (at its start, or at the first pulse of an
  old save), since no save was at hand to measure 1836's.

Read first: `docs/systems/mod_systems/demographics.md` § Dynastic Wealth per
state; `docs/systems/mod_systems/inheritance.md`; and the flat-crew design
(`docs/superpowers/archive/specs/2026-10-16-ai-managed-flat-staff-design.md`),
whose engine facts this reuses.

## The request (owner, 2026-11-28)

> Something that I think the game currently does not model is concentration of
> wealth within the capitalist class. The mod has attempted to model this
> through the dynastic wealth system. However I think an additional way that we
> could model this is to make financial districts and company headquarters have
> a component of employment that is unscaled and a component that like the
> entire current employment is level scaled. What this would mean is that as
> the company grows or the financial district owns more building levels the
> capitalists per level will go down. This should then also feed into our
> dynastic wealth measurement.

## 1. Today

### 1.1 Who an ownership building employs

Every ownership method puts its whole staff in `level_scaled`, so a building
of level L employs L times what a level-1 building does. The dividend shares
are already `unscaled`.

Financial District (`pmg_ownership_building_financial_district`; the mod's
values, `extra_pms.txt`):

| Method | Capitalists a level | Others a level | Shares |
|---|---|---|---|
| Privately Owned | 50 | 20 shopkeepers, 20 clerks, 10 academics | capitalists 10, shopkeepers 1 |
| Publicly Traded (Mutual Funds) | 50 | 25 academics, 25 clerks | capitalists 10 |
| Divine Economics II–V | 50 | 25 clergy, 25 clerks | capitalists 10, clergy 2 |
| Electronic Brokerage (Transistors) | 30 | 10 academics, 10 clerks | capitalists 10 |
| Digital Trading (Computer Networks) | 20 | 5 academics | capitalists 10 |
| Automated Trading (Digital Telecommunications) | 10 | 5 academics | capitalists 10 |
| Hobbyist Management (Post-Scarcity) | 0 | 5 academics | academics 10 |

Company headquarters (`pmg_ownership_building_company_headquarter`, one group
for headquarters and regional headquarters):

| Category | Capitalists a level | Co-owners a level | Staff a level |
|---|---|---|---|
| Capitalist-owned | 25 | | 20 clerks, 5 academics |
| Aristocrat-owned | 10 | 15 aristocrats | 20 clerks, 5 academics |
| Aristocrat-owned, Commercialized Agriculture | 15 | 10 aristocrats | 20 clerks, 5 academics |
| Shopkeeper-owned | 10 | 25 shopkeepers | 10 clerks, 5 academics |
| Bureaucrat-owned | 10 | 25 bureaucrats | 10 clerks, 5 academics |
| Academic-owned (vanilla's, not replaced) | 10 | 25 academics | 15 clerks |
| Divine Economics copies (six: the capitalist one replaced by the mod, five vanilla) | 10–20 | as their category | 25 clergy |
| Government-run (five) and cooperative (five) | 0 | | bureaucrats or shopkeepers and clerks |

The Financial District's three tiers and Hobbyist Management sit in the
headquarters group too (`extra_pm_groups.txt`), shared between both buildings.

So the owners a level of property are constant. A Financial District of 100
levels has 100 times a level-1 district's capitalists: the capitalist class
grows in step with the capital it holds, a larger fortune is shared by
proportionally more people, and a capitalist's dividend doesn't rise with the
size of the holding. The tiers are the only fall today, and they follow
technology, not size (50, 30, 20, 10 a level).

### 1.2 How the buildings get their levels

- **A Financial District** is built and expanded by the investment pool like
  any other building.
- **A headquarters or regional headquarters** is `buildable = no`,
  `expandable = no`, `downsizeable = no`: the engine sets its level. Paradox's
  [dev diary 127](https://admin-forum.paradoxplaza.com/forum/developer-diary/victoria-3-dev-diary-127-bulk-nationalization-and-companies-building-ownership.1702140/latest)
  says the level rises with each level the company builds or buys, and
  [dev diary 147](https://admin-forum.paradoxplaza.com/forum/developer-diary/victoria-3-dev-diary-147-everything-companies.1747321)
  that a regional headquarters opens in a country where the company owns at
  least 5 levels (`COMPANY_MINIMUM_LEVELS_PER_HQ = 5`). So a headquarters'
  level is the company's size, which makes it the cleanest case for the
  request. Not yet read in this mod (§ 9, fact 3).
- The engine makes a building type for each company type, so a headquarters
  is found by group (`te_demog_is_ownership_building` already does this).

### 1.3 What Dynastic Wealth reads of them

- **The ownership term** leaves them out: they read as self-owned.
- **The national figure's weights** count each of their levels as 1
  (`te_dg_lv_own`).
- **The income inequality term** reads the Gini, which sees the capitalists'
  wealth bands, so richer capitalists already raise it. It stops at +15 (a
  shown Gini of 0.775); the 2054 save's median state, at 0.64, sits at +9.6.
- **Nothing reads how large a fortune is or how many people share it.**

## 2. The proposal in brief

1. **Split the owners' employment into a fixed partnership and a per-level
   part.** The partnership goes in `unscaled` (once a building), a smaller
   per-level part stays in `level_scaled`, and the staff (clerks, academics,
   clergy) stays per level. The partners don't multiply with the assets; the
   back office does. A building of level L then hires a + N/L owners a level:
   N + a at level 1, falling toward a.
2. **The engine pattern has shipped.** An `unscaled` employment add counts
   once a building: the flat-crew methods have used it since 1.1.9 (widened in
   1.3.2), after the design gated their rollout on the `ai_managed_flat_staff`
   self-check.
3. **Fewer owners share the same dividends, so each is richer.** With
   a = 20 and N = 300, a level-100 Financial District has 2,300 capitalists
   against 5,000 today, and each takes 2.2 times the dividend. The Gini picks
   that up with no further change.
4. **A ninth Dynastic Wealth target term, Scale of Fortunes,** reads the
   property per owner in each state's ownership buildings, so the score sees
   the concentration directly (§ 5).

## 3. Which methods change

- **Whose employment splits:** capitalists in every method that employs
  them, and aristocrats in the two aristocrat-owned headquarters methods
  (call 1). The shopkeepers, bureaucrats and academics of their categories'
  headquarters stay per level: those are the broad-based companies, and an
  owner class that grows with the company is what makes them broad.
- **The tiers** scale the partnership and the per-level part by today's ratio
  to the base method (Electronic Brokerage 0.6, Digital Trading 0.4, Automated
  Trading 0.2), so a tier still cuts the owners by its share at every size
  (call 3).
- **Government-run and cooperative headquarters are unchanged.** They hold no
  private fortune, and staff that grows with the company is the contrast the
  player sees.
- **Regional headquarters share the group,** so each office gets its own
  partnership (call 7).
- **Manor Houses** aren't in the request (call 4).
- **The Creditors' Consortium** (`pm_hq_creditors_consortium`, 2,000
  capitalists a level) is a power bloc headquarters method, not an ownership
  building, and stays as it is.

That is 18 methods with capitalists: the district's three base methods, the
three shared tiers, and twelve headquarters methods (six categories, six
Divine Economics copies). Six of them are vanilla's only (the academic-owned
method and five Divine Economics copies) and need a `REPLACE:` of their own.

## 4. Sizing

A method that employs T owners a level today gets a partnership N and a
per-level part a. The break-even level L\* is where N + a·L\* = T·L\*, so
N = (T − a)·L\*.

Owners a level of a Privately Owned Financial District (T = 50):

| Level | 1 | 3 | 5 | 10 | 25 | 50 | 100 | 200 |
|---|---|---|---|---|---|---|---|---|
| Today | 50 | 50 | 50 | 50 | 50 | 50 | 50 | 50 |
| A: N = 300, a = 20 (break-even 10) | 320 | 120 | 80 | 50 | 32 | 26 | 23 | 21.5 |
| B: N = 150, a = 20 (break-even 5) | 170 | 70 | 50 | 35 | 26 | 23 | 21.5 | 20.8 |
| C: N = 600, a = 10 (break-even 15) | 610 | 210 | 130 | 70 | 34 | 22 | 16 | 13 |

A capitalist's dividend at level 100 against today: A 2.2 times, B 2.3, C 3.1;
at level 200: A 2.3, B 2.4, C 3.8.

The two numbers pull against each other. A small a gives a strong late
effect; a large N with a small break-even puts many owners into small buildings
early. The level-1 district is the risk: under A it hires 320 capitalists where
it hires 50 now, and under C 610. So the break-even comes from saves: the
distribution of district and headquarters levels by era (§ 9, M1). A starting
point: a at 40% of today's per-level figure, as in A, and the break-even at the
median district level of an 1890 save. For the headquarters at the same shape,
the capitalist-owned method (25 a level) is N = 150, a = 10, and the
10-capitalist categories N = 60, a = 4.

## 5. Dynastic Wealth

### 5.1 What follows with no change

- Richer capitalists raise the Gini, so the income inequality term rises up
  to its cap of +15.
- The national figure's weights are levels, so they don't move.

### 5.2 A new target term: Scale of Fortunes

- **What it reads:** r, the levels of property the state's privately held
  ownership buildings own, per 1,000 owners they employ. A building's owned
  levels are its `num_building_assets_of_group(<group>)` summed over the
  top-level building groups (vanilla reads that value link in an interest
  group's script value, `workplace.num_building_assets_of_group(bg_military_industry)`).
  Its owners are the walk's capitalists (and aristocrats in the aristocrat-owned
  headquarters) whose workplace is one of those buildings; the walk already
  tests each pop's workplace (`te_demog_walks`).
- **Its shape:** K × log₂(r ÷ r₀), with r₀ the 1836 median measured on a save,
  so that 1836 starts near 0 (the ownership and income terms were centred the
  same way). At most +10, at least −5 (call 5). The mod already computes a
  logarithm in script (`te_demog_wc_log_growth`'s atanh series).
- **Why measured rather than derived from levels:** it counts partner slots
  left unfilled (fewer owners, larger shares: concentration all the same), the
  tiers, and what each building actually owns, which a district's level need
  not track. If the asset read fails, the fallback derives the owners from the
  methods (n·N + a·ΣL over the state's n buildings) and the property from their
  levels.
- **Per state,** where the fortunes are held, so the national figure takes it
  in through the ownership-level weights, and a capital full of large districts
  carries Concentrated Property while the country sits lower.
- **Wiring,** as the ownership term's: the target's sum, a stored
  `te_dg_wc_t_scale` for the Demographics tab's bar, loc on the bar and the
  concept, the target's tooltip. It is measured, so no law carries it.

### 5.3 Two terms from one cause

The Gini and Scale of Fortunes both rise when the partnership shrinks. The Gini
reads how income is spread; the new term reads how large a holding is and how
few share it. Keeping the new term's cap below the income term's (+10 against
+15) keeps the two together within reason, and the target is clamped 0–100.

## 6. Side effects to watch

- **The Industrialists' clout.** Fewer pops, each richer. The snapshot's
  defines don't say whether political strength from wealth rises as fast as the
  headcount falls. If it doesn't, concentration weakens the class it
  concentrates, the reverse of what the request models. Great Family Fortunes
  (+20% clout at 80) leans the other way. Measure (§ 9, M3).
- **The wealth ceiling.** The mod's `NUM_WEALTH_LEVELS` is 200. Capitalists
  move nearer it, and past it neither the Gini's stand-in nor their spending
  sees more.
- **Demand.** Fewer, richer capitalists may buy fewer luxury goods in total,
  as a richer pop spends a smaller share of each extra unit of income.
- **The investment pool.** Dividends don't change in total, so the pool
  should move little. Ownership buildings pay wages too
  (`BUILDING_WAGES_OWNERSHIP_BUILDING_FACTOR` 0.75), so a smaller staff leaves a
  little more to pay out.
- **Jobs in a running game.** On load, a large late-game district has more
  capitalists than slots, and the engine lays the surplus off over the
  following weeks. Small districts hire more, as far as capitalist
  qualifications allow.
- **Hiring.** A building hires at most a tenth of its positions a week, and no
  profession more than 10 points ahead of another
  (`EMPLOYMENT_PROPORTIONALITY_LIMIT`), so a partnership left short holds back
  the clerks.
- **The AI's method choice.** Both ownership groups choose `most_productive`.
  Check that the AI still moves to the tiers.

## 7. Found on the way (already in `main`)

1. **The shared tiers carry no category or law gate in the headquarters
   group.** Electronic Brokerage, Digital Trading and Automated Trading list
   only a technology, so under Command Economy or Cooperative Ownership a
   headquarters can take one and employ capitalists with capitalists' shares.
   On an aristocrat-, shopkeeper-, academic- or bureaucrat-owned headquarters a
   tier replaces the category's owners with capitalists (10 to 30 a level), and
   on a capitalist-owned one Electronic Brokerage raises them (25 to 30). The
   split rewrites these methods anyway, so headquarters copies of the tiers for
   each category, hidden when unavailable as the government-run and cooperative
   copies are, fit in the same build (call 8).
2. **The Divine Economics copies disagree.** The mod's `REPLACE:` of
   `pm_company_headquarter_principle_divine_economics_2` extends it to
   principles IV and V and drops vanilla's
   `unlocking_company_categories = { capitalist_owned }`; the five vanilla
   category copies still list II and III only. So under IV or V a
   non-capitalist headquarters appears to lose its own copy, and any category
   to be offered the capitalist one. Confirm in a headquarters panel; the split
   touches all six.

## 8. What a build touches

- `common/production_methods/extra_pms.txt`: the twelve replaced methods, six
  new `REPLACE:` blocks, the tier copies if call 8 says so; the `# Employment`
  headers `pm_costs.py` writes (a full reload, not `audits_only`).
- Tests: `test_flat_crews.py` and `test_ai_managed_flat_staff.py` read any
  `unscaled` employment as a full flat crew, which must be 1,000 strong and
  carry `building_job_attractiveness_mult`. They already exempt the four
  ownership buildings from the token-crew rule and need the same exemption for
  a partnership. A new test pins the split: owners flat and per level, staff
  per level, tiers in proportion.
- Dynastic Wealth: the walk (`te_demog_effects.txt`), a generated list of the
  top-level building groups, the term in `te_demog_values.txt`, its store in
  `te_demog_wc_national` (`te_demog_wealth_effects.txt`), the panel's bar and
  its loc, and `test_demographics_registry.py`.
- The self-checks of § 9 and their rows in a play-test list.
- Docs: `demographics.md` § Dynastic Wealth per state; the player guide's
  `06-politics.md` (the paragraph that lists the target's terms), and the PDF.

## 9. Engine facts and measurements

Facts, each a once-a-game `TE_SELF_CHECK OK|BROKEN` line:

1. **An `unscaled` employment add counts once on an ownership building.** It
   was read on production buildings; headquarters are engine-made.
   `ownership_partners`: a district and a headquarters of level 5 or more,
   `modifier:building_employment_capitalists_add` about N + a·L (the
   `ai_managed_flat_staff` read, `te_aipm_selfcheck_values.txt`).
2. **`num_building_assets_of_group` works as a value on a district and a
   headquarters, and a parent group counts its children's levels.**
   `ownership_assets`: a headquarters' summed assets against its level.
3. **A headquarters' level is its company's owned levels,** as the dev diary
   says. `company_owned_levels` is a comparison trigger only, so the read is a
   ladder.

Measurements on the owner's saves (`scripts/analysis/`):

- **M1.** District and headquarters levels by era (1836, 1890, 1950, 2050):
  the break-even.
- **M2.** r₀, levels owned per 1,000 owners in 1836: the new term's centre.
- **M3.** An observer run to 1950 with and without the split: capitalists,
  Industrialist clout, capitalist wealth, the Gini, Dynastic Wealth, the
  investment pool.

## 10. Open calls

1. **Whose employment splits:** capitalists only, or the aristocrats of the
   aristocrat-owned headquarters too? Recommended: both, since each holds 10
   shares there.
2. **The break-even and the asymptote.** Recommended: settle after M1,
   starting from A's shape (a at 40% of today's, the break-even at the median
   1890 district level).
3. **The tiers:** in proportion (recommended), or the same partnership with a
   deeper per-level cut.
4. **Manor Houses too?** Recommended: not now. Land tenure already scores
   landed fortunes, and the request is about capitalists.
5. **Dynastic Wealth:** the Gini alone, or Scale of Fortunes as well.
   Recommended: the term, at most +10 and at least −5, centred on 1836.
6. **The term measured from owned assets** (recommended, behind fact 2's
   self-check) **or derived from levels.**
7. **Regional headquarters get their own partnership.** Recommended: yes.
8. **Fix § 7 in the same build.** Recommended: yes, since the build rewrites
   those methods.
9. **Old saves:** the engine re-staffs on load. Recommended: no migration.

## 11. Build order

Two PRs. The first is the split, its tests and self-check, and the tier copies
if call 8 says so; on its own it moves dividends and the Gini. M1 sets its
numbers, and M3 reads it afterwards. The second is Scale of Fortunes, once M2
gives its centre.

## 12. Not changed

The dividend shares, the districts' investment scores, the government-run and
cooperative headquarters, the power bloc headquarters, Manor Houses (unless
call 4 says otherwise) and the national figure's weights.
