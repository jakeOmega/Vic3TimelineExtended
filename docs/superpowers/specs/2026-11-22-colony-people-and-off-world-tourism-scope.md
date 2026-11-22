# Colony people as the limit on modules, and a Resort Colony free of its state: scope

Drafted 2026-11-22 from a discussion with the owner. This is a scoping document:
what to build, in what order, and the calls still open. It is not yet a design,
and it has no implementation plan. Later sessions write both.

It covers two pieces of work that share a subject and little else:

- **Part A (small):** the Resort Colony's Tourism stops following the Earth
  state the building stands in.
- **Part B (a design of its own):** a colony's people, not its slots, limit its
  modules.

Read first: `docs/systems/mod_systems/space_race.md` §§ Colony population,
Colony modules and Extraplanetary Base room, Autonomy; the Resort Colony design
(`2026-11-21-resort-colony-building-design.md`, on #1950's branch until it
merges); and the ground-types design
(`2026-11-05-extraplanetary-base-ground-types-design.md`).

## Decisions (owner, 2026-11-22)

**The Earth state**

- **Tourism output bonuses are meant to be large, and stay.** In the owner's
  words: "tourism's placement is not merely a matter of wage and capital
  expenditure. Throughput can be countered by building more levels of tourism
  industry and the only downside is that it employs more people. By having
  these output modifiers a resort in Hawaii with good transportation access can
  dramatically outperform a tourism industry in an underdeveloped Kansas."
- **They should not reach the Resort Colony.** "The local conditions of the
  operations of a space resort on Earth shouldn't significantly affect the
  profitability of that space resort. Only the ordinary terrestrial tourism
  industry." This answers #1953: scope it, don't cap it.
- **The country's Tourism modifiers still reach it** (laws, Axiom Space, bloc
  principles, cultural hegemony). They are about the country, not the place.
- **The Spaceport's +1% throughput an Airport level stays.** It is the one
  Earth link kept on purpose.
- **Not in scope:** Digital Access being a local good, and levels going with
  the state when it changes hands, are "reasonable abstractions". Economy of
  scale is already off for `bg_exotic`, and the crew is unscaled, so neither
  ties the building to its state.
- **How:** a modifier on the building that cancels the state's share. The
  state's share is the state's reading less the country's. The owner has seen
  a building's modifier sum with the state's in earlier versions; it is not
  verified on a recent one.

**People**

- **Slots go. People limit modules. The Habitat is the only capped module**,
  with a soft maximum.
- **The panel must say what the crews are doing.** The owner has so rarely seen
  crews matter that it is unclear how well the panel explains them.
- **Settlers: pay more, send more, with no fixed top.** "If you have the
  population and the launch capacity, I don't really see what limit there is in
  moving people to your new colonies."
- **The five technologies that give a slot** give more people per Habitat or
  more Habitat slots instead (the owner leans to either over smaller crews).
- **More people raising autonomy is welcome**: "currently autonomy very rarely
  matters." It needs a balance check.
- **A world's own base and resort room stays automated.** A colony with no
  people is a fully automated mine, and given autonomy that is a fair strategy.
- **Order:** Part A follows #1950 directly. Part B is designed after the
  ground-types build lands, since both rework the Modules view.

## 1. Today

### 1.1 What reaches the Resort Colony from its state

Tourism is 60% of a Resort Colony level's output value (900 Tourism, £90,000 of
£150,000). `goods_output_tourism_mult` works by good, so every state-scope
grant reaches every Tourism producer in the state:

| State-scope source | Size |
|---|---|
| The state's appeal (`tourism_output`, refreshed monthly by `te_update_tourism_modifier`) | the Hawaii-against-Kansas figure |
| Airport and Spaceport methods | +15% a staffed level |
| Other transport methods, monuments, local modifiers | +2.5% to +25% each |
| Pollution (`state_region_pollution_general`) | up to −200% |
| Turmoil, obstinance | up to −100%, −50% |

The sum is clamped at −100%, which zeroes Tourism in a state in crisis. That is
intended for the Tourism Industry. For a resort on the Moon it means the best
site is a clean state with a big airport, and a polluted industrial state can
shut it.

Issue #1953 named only the Airport. The whole list is in scope.

### 1.2 What a colony's people do

- **Crews:** one per 5,000 people (`CREW_PER_LEVEL`). Staffing is
  (crews + 1) ÷ crewed levels, at most 1, and scales every specialization and
  facility. Habitats aren't crewed.
- **Prestige and cultural pull:** +1% and +2% per 100,000 people off Earth, at
  most ten times.
- **Autonomy:** +0.05 a month per 10,000 people, against a pull of home of
  −0.25.
- **Also:** militia (a battalion a 20,000), war support, a colony's own builds
  (autonomy × people), the free-colony threshold.

Crews rarely bind, for two reasons:

- **Slots run out first.** A world has 1 to 4 slots (84 in all) and room for
  10,000 to 50,000 people (945,000 in all), so 2 to 10 crews at full room. Only
  the ten smallest worlds (10,000 people, 1 slot) can run short, and only with
  all four specialization levels built.
- **Artificial Intelligence waives crews entirely.** It is era 12. Three of the
  five slot technologies are era 12 and one is era 13, so the slots grow just
  as the crews stop counting. From era 12 on, people give only prestige,
  autonomy pressure and militia. The Resort Colony is era 12 too.

## 2. Part A: the Resort Colony leaves its state's Tourism bonuses

**The rule.** A Resort Colony makes the Tourism its world's draw, its room and
the country's modifiers give, whatever state the building stands in. Fine Art is
unaffected today and stays so.

**The mechanism.** A pair of static modifiers on the building, a bonus and a
penalty with `goods_output_tourism_mult = ±0.01`, applied to each Resort Colony
at a multiplier equal to the state's share with its sign reversed. The
ground-types build already puts goods-output modifiers on each Extraplanetary
Base this way (`sr_eb_apply_mix`: `every_scope_state`, `every_scope_building`,
a bonus and penalty pair at a multiplier), so the pattern and half of the engine
question come with it.

**For the design to settle:**

- **Reading the state's share.** State reading less country reading, as the
  owner proposes. The refresh can't read a modifier in the effect that just
  added it, so the cancel either runs on a later pulse than
  `te_update_tourism_modifier` or reads the stored values. It is at most a
  month behind a change in the state, which is acceptable.
- **The clamp.** If the engine sums the building's modifier with the state's
  before clamping at −100%, the cancel is exact. If it clamps first, a zeroed
  state would leave the resort far above par. The fallback then is to cap the
  cancel at +100%, which holds a zeroed state at par and is exact everywhere
  else.
- **One refresh site**, with the old copy removed first, on the state's pulse
  (the modifier is on a building in a state).

**Verifying it.** A once-a-game `TE_SELF_CHECK` line if script can read the
building's own modifier total; otherwise an item on
`docs/testing/solar-colonies-playtest.md` (a Resort Colony in a state with a
large Airport, and one in a heavily polluted state, both at their draw). If the
building-scope sum fails altogether, the fallback is a separate off-world good
in the same pop need, which is a larger change and would come back to the owner.

**What the player sees.** The building's output breakdown shows the state's
lines and one named line that takes them off. The Resort Draw concept and the
guide's Resort Colony section say that the state doesn't matter and the
Spaceport's launch bonus does.

**A sweep, in the same PR.** State-scope grants of `goods_output_fine_art_mult`
and of the Extraplanetary Base's seven goods, through `/modifier-grants`. Any
that reach these two buildings from a state get the same treatment, or a line
in the PR saying why not. A first look found none of size, but it was a grep,
not the endpoint.

**Size.** One small PR after #1950 merges: two static modifiers, one effect, a
pulse hook, loc, a test, the play-test item, and a few sentences in
`16-space.md`. It closes #1953.

## 3. Part B: people limit modules

### 3.1 The rule

- **No slots.** Any module may be queued at any colony at the flat price.
- **Crews are the limit.** Each crewed level past the first needs a crew, as
  today. A colony short of crews runs every crewed module at the same share,
  as today.
- **This is already a soft cap.** Staffing is (crews + 1) ÷ levels, so the
  staffed levels of a colony sum to crews + 1 however many are built. A module
  past the crews adds nothing in total and thins the rest. It needs no new
  penalty.
- **Specializations keep their four levels**, a hard cap, as now. Their
  modifiers are large.

### 3.2 Habitats

The Habitat is the one module with a cap. The world's `slots` figure (1 to 4)
becomes its Habitat cap. Past the cap, the rising price that slots have today
moves to Habitats alone: the n-th past costs (1 + n) times the price, up to 8
past. Module Storage's sizing follows the dearest Habitat.

### 3.3 The five slot technologies

Nuclear Thermal Propulsion, Orbital Manufacturing, Advanced Nanofabrication,
Space Colonization and Molecular Assemblers each give +1 slot today. The two
replacements the owner favors, with the people they allow when every world is
built out (from the site table, at 5,000 a crew):

| Option | People, all 40 worlds | Crews | Himalia (10,000, cap 1) | Valles Marineris (50,000, cap 4) |
|---|---|---|---|---|
| Today's Habitats within the table's caps, no technology | 2.15 million | 430 | 15,000 | 150,000 |
| **More people per Habitat**: +10% of base room each, so 100% with all five | 3.36 million | 671 | 20,000 | 250,000 |
| **Habitat slots**: +1 cap each | 4.51 million | 902 | 40,000 | 275,000 |

For comparison, today's slots with all five technologies hold 284 slot modules.

**Recommendation: more people per Habitat.** It keeps the table's difference
between a small world and a large one (Himalia stays an outpost), and it asks
for no extra modules to be queued and shipped to get the benefit.

### 3.4 Artificial Intelligence

It stops waiving crews. Recommendation: it halves the crew a level needs
(2,500 people), so it is still a large prize and people still count after it.

### 3.5 Settlers

- **No fixed top.** The program's level becomes an amount, stepped up and down
  by doubling from 500 a month.
- **The bill is Launch Capacity per settler.** Today's +5% Space Program
  throughput a level can't carry an open-ended rate: fabrication points and
  Module Storage are workforce-scaled on the same building, so more throughput
  is partly a reward. Recommendation: a modifier on the Space Program building
  adding Launch Capacity input at a multiplier of the settlers sent, the same
  building-scope pattern as Part A. Today's three levels should cost about what
  they do now.
- **Three limits remain**, as the owner said: people at home, Launch Capacity
  (its price rises as the program buys more) and room at the colonies.
- **Where they come from.** Today all settlers leave the Space Program's state.
  At tens of thousands a month that would empty it. Recommendation: from the
  country's incorporated states by population.
- **No reward for toggling**, per the design defaults. Settlers are sent
  monthly whatever the launch windows, as today.

### 3.6 Autonomy

People press on autonomy at +0.05 a month per 10,000. With the pull of home at
−0.25, a colony of 50,000 is neutral, and Valles Marineris at 250,000 would
gain a point a month before distance: it would break away unless chartered
(−0.4) or held by about seven Administrations (−0.15 each, each needing a
crew). So autonomy, not the Habitat cap, becomes the practical limit on a
large colony, and Administrations compete with every other module for crews.

This is the tension the owner wants. The design should tabulate where colonies
of several sizes settle, as the colony management design § 4.2 does, and retune
the people term or the Administration if a built-out colony can't be held at
all.

### 3.7 Modules that add room

A staffed Mining Complex adds 50 Extraplanetary Base room at its world, and
after #1950 a staffed Off-World Resort adds 10 Resort Colony room. Without
slots, a colony with 50 crews could add 2,500 base room at one world whose own
room is at most 300, against 4,325 in the whole table. The ground-types
checkbox moves levels to the site that earns most, so cheap room at the best
site would empty the others and flatten the choice of ground.

The design must answer this. Candidates:

- a world's module room counts in full up to its own table room and at half
  past it;
- room modules need two crews a level;
- leave it, if the arithmetic shows autonomy and the price of settlers hold it
  down.

### 3.8 The AI

- The module plan already tests crews for specializations and facilities. "Slot
  modules only within the world's slots" becomes "only what its crews can run",
  and a Habitat within the cap once people fill three quarters of the room.
- This also bounds the loop #1950 left for the owner (an AI adding an Off-World
  Resort a year in place of Research Stations): it stops at the crews.
- Settlers: a share of weekly income, as fabrication has (5%).
- A colony's own builds stay within its crews and its Habitat cap, where today
  they stay within its slots.

### 3.9 The panel

The owner's requirement: a player must see when crews limit a colony and what
to do about it. Today the Modules view shows a Crew share, the page a Modules
Crewed tile, and the People view each colony's crews. None shows crews needed
against crews available. Scope:

- **Crews as a pair of numbers** where Slots is today: needed / available, red
  when short, with the share beside it.
- **The + button says what the next module does**: "needs a crew, 2 to spare",
  or "no crew to spare: every module here would run at 71%".
- **Habitats:** levels over cap, and the next one's price.
- **People view:** crews, and how many people the queued modules will need.
- **Overview:** a count of understaffed colonies, with their names on hover.
- **Solar System:** each world's Habitat cap and room in place of its slots.
- **The How it Works text and the concepts** rewritten around people.

The ground-types build is redoing the Modules view's base cells and #1950 adds
the Resort Room tile, so this pass starts from whatever they leave.

### 3.10 What else reads people

Each will see larger numbers and wants a look in the design: the off-world
population bonus (its cap of a million people is now easy to reach), militia
and the garrison a seizure needs, war support's weight for a full colony
(75,000 people), a colony's own build rate, the AI's price for a colony in a
cession, and the Demographics census, which counts settlers as emigrants.

### 3.11 What goes

`country_sr_colony_slots_add` and its five grants, the Slots cell and its
hover, the slot tests in every queue trigger, and the rule that the queue takes
a module only while the stock can hold its price (kept for Habitats). Old saves
are not repaired, as for #1950.

## 4. Build order

1. **Part A**, after #1950 merges. One PR. Closes #1953.
2. **Part B's design**, after the ground-types build merges: this scope's open
   calls answered, the numbers tabulated (§§ 3.3, 3.6, 3.7), the panel drawn.
3. **Part B's build**, likely in three stages in one PR or a short stack:
   the rule (slots out, Habitat cap, technologies, Artificial Intelligence,
   the AI); settlers; the panel and the guide.

Both parts update `docs/player_guide/16-space.md` and rebuild the PDF. Part B
also updates `02-timeline.md` where the five technologies are described.

## 5. Open calls

Each has a recommendation. None blocks Part A except the last two.

1. **The slot technologies' reward:** more people per Habitat (recommended) or
   Habitat slots (§ 3.3).
2. **Artificial Intelligence:** halve the crew (recommended), or another
   figure (§ 3.4).
3. **A colony short of crews:** every module at the same share, as today
   (recommended, no new control), or an order the player sets.
4. **Modules that add room:** which of § 3.7's answers.
5. **Settlers' bill:** Launch Capacity per settler on the Space Program
   building (recommended). Should a farther world cost more per settler?
6. **Settlers' origin:** all incorporated states by population (recommended),
   or the Space Program's state as today.
7. **Past the Habitat cap:** keep today's 8 at a rising price (recommended).
8. **Part A, a state zeroed by pollution or turmoil:** cancel it in full, so
   the resort is at par (recommended, it is what "the state doesn't matter"
   means), or let a state in crisis still hurt it.
9. **Part A, turmoil specifically:** a strike or unrest in the state is local
   to the ground crew. Cancel it with the rest (recommended), or keep it as
   the one local penalty.
