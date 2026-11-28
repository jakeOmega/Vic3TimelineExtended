# Actors With Interests of Their Own: the Chassis, and Firms as the First Slice

Date: 2026-11-28. From the owner's brainstorm of the same day. The owner set
the principles in § 3, the scope of the first slice (§ 2), the answers to a
petition and the weighting of defection (§ 7), the tiers of action (§ 4.6)
and the rules for AI countries (§ 12); those rulings are marked **owner**.
Everything else is the designer's call, and the owner may revisit any of it
with a stated reason. All numbers are first guesses for the builder to tune.
Nothing here is built.

**Widened the same day (owner).** The first version exists to prove the actor
system, and it can't be judged on an actor with one dimension. So the firm is
built out: eight goals where there were five, seven kinds of holding where
there were three, and four chains at home beside the one abroad. The owner
approved the five additions: politics at home (§ 8), the workforce (§ 9),
technology (§ 10), relief (§ 11) and the foundation (§ 5.5). § 2 has what
that changes in the scope. The owner then ruled on the ten open decisions;
§ 18 records each ruling and where it is written into the design.

Background: `docs/vanilla/vanilla_politics_reference.md`
§§ 3 to 6, 8 and 9, `docs/vanilla/vanilla_diplomacy_reference.md` § 9,
`docs/systems/mod_systems/ai.md` § "Company AI",
`docs/systems/mod_systems/amendments.md`,
`docs/systems/mod_systems/judiciary.md`,
`docs/systems/mod_systems/banking_cycle.md`,
`docs/systems/mod_systems/covert_warfare.md` § "New operations",
`docs/systems/mod_systems/state_and_nation_panels.md`.

## 1. Why

A country in this mod is run by one will: the player's or the AI's. Everything
inside it either obeys or grades. Interest groups approve or disapprove,
movements press for a law, and companies do nothing at all: they hold
buildings and pay dividends. None of them wants something and goes to get it.

History from 1800 to now is full of bodies inside and across countries that
did exactly that, often against their own government or without asking it:

- Chartered and concession companies that drew their governments into
  territory nobody in the capital had planned to take (the Royal Niger
  Company, the British South Africa Company and the Jameson Raid, the
  concessions in Persia and China).
- Firms that had a foreign policy of their own (United Fruit in Guatemala,
  Anglo-Persian in 1953, ITT in Chile, the Western firms that stayed in
  Germany in the 1930s).
- Trusts and cartels that set prices, bought legislatures and fought the
  courts (Standard Oil, the German coal and steel syndicates, De Beers, the
  Phoebus lamp cartel).
- Missions, unions, parties and creditors that did the same in their own
  fields.

Science fiction extends the line: the megacorporation with its own army, the
company town grown into a company state, the off-world colony whose owners'
interests drift from the home country's.

This spec is the frame for modelling such bodies as **actors**, and the design
of the first kind of actor, the **firm**.

## 2. Goals and non-goals

**Goals**

1. A chassis any kind of actor can sit on: a goal derived from the actor's
   real position, currencies it earns and spends, holdings it builds and
   defends, a turn in which it acts, and a surface that shows all of it.
2. Firms as the first actors, on the mod's and vanilla's existing companies
   (**owner**: firms first, because companies have no agency at all today, so
   the difference will be plain in play).
3. One kind of actor, built out (**owner**). The first ruling was narrow but
   deep: few kinds of actor and of action, each tied into other systems and
   legible, so that it reads as part of the world. That still holds for the
   kinds of actor: firms only. Within the firm the owner widened it, because
   a firm that only forms cartels and takes concessions shows whether two
   chains work, not whether the chassis does. The test of the chassis is
   that:
   - goals compete, so a firm changes what it wants as its position changes,
     and a weak firm wants something too;
   - one currency is wanted by unlike verbs, so spending it is a choice;
   - firms disagree with each other, and not only with the state;
   - the player sometimes wants a firm strong.

   So five chains: the trust (§ 6) and pulled abroad (§ 7) at full depth,
   politics at home (§ 8) at full depth, and the workforce (§ 9), technology
   (§ 10) and relief (§ 11) as shorter chains that reuse the others' verbs.
4. AI countries subject to all of it, with every push on an AI government
   visible and attributed (§ 12).
5. Hooks for the actors that follow (§ 15), and for firms that come into being
   and dissolve with their sector's concentration (the owner's long-run
   direction, out of scope here).

**Non-goals**

- Any actor other than firms: organized labor, political movements, religious
  organizations and industry associations are designed only as far as the
  chassis must allow for them (§ 15).
- Replacing vanilla's company slots, or founding and dissolving companies from
  script. The mod's existing rule that has an AI country drop a company
  after five failing years (`docs/systems/mod_systems/ai.md`, "Failing
  companies") stays as it is, and § 11 reads its counter.
- Banks' lending verbs, capital flight, takeovers of one firm by another, and
  a firm moving its seat to another country.
- A firm switching production methods in its buildings. The player sets
  those, and an actor that changed them would be fighting the player for a
  control the game gives the player.
- The state as a firm's customer: arms firms pressing for rearmament, war
  scares, sales to both sides. It needs ties of its own to War and Treaties,
  and is the first thing to add after this slice (§ 15).
- State-run counterparts (a state union, an established church, a national
  champion as a thing the state builds). **Owner**: those are laws,
  institutions and treaties, under different forces from private holdings,
  and stay outside this system. They act as its environment: they set which
  holdings are legal, what they cost and which are protected abroad.

## 3. Principles

All **owner** unless marked.

1. **The ten-year test.** If the player touches nothing for ten years, the
   actors must still have changed the world. A body that only grades the
   player's actions is a lobby, and this is not a lobby system.
2. **Three targets.** An actor acts on itself, on other actors and on the
   state. The player often feels an action second-hand.
3. **Approval is one channel among several.** A move may work mainly through
   interest-group approval, loyalists or radicals, and those have real
   effects. Across the system they must not be the only consequence or the
   largest share of consequences.
4. **Active effects lead; modifiers are welcome inside a system.** The Space
   Race colonies give plain modifiers and feel alive because the thing that
   gives them can be built, defended and attacked. § 4.4's holdings are that
   pattern.
5. **Derived, never assigned.** An actor wants what its position implies: what
   it owns, buys and sells, where its assets sit, which law binds it
   (designer).
6. **Self-interest is not the whole motive.** Actors are made of people with
   national, ideological and personal loyalties. A small French company in
   Africa does not turn to Germany because Paris ruled against it. It may turn
   to a power France does not see as an enemy, and it is bolder the more
   powerful it is (§ 7.5).
7. **Lasting harm is allowed** where the player has a view of it, an alert
   (the Space Race's module-queue alerts are the model) and an action that
   counters it.
8. **Secrecy below the top tier.** Actors may act in secret, but not in their
   most consequential actions (§ 4.6).
9. **No hidden switch in an AI government** (§ 12).
10. The design defaults of `CLAUDE.md` hold: soft caps in place of eligibility
    gates, and no setting worth toggling. The player sets a posture and the
    actor plays itself.

## 4. The chassis

### 4.1 The actor

An actor is a record on a **host** scope the engine already has. In this slice
the host is a company; § 15 gives the movement as the second host. The record
holds:

| Field | Meaning |
|---|---|
| Home | The country the host belongs to |
| Sector | The building types and goods it lives on (§ 5.1) |
| Goal | The one aim it is pursuing now, with its reason (§ 5.2) |
| Currencies | Funds, Connections, Standing (§ 4.3) |
| Holdings | The standing positions it has built (§ 4.4) |
| Temperament | Read from its leading character (§ 5.3) |
| Condition | How it is doing: its prosperity and the business cycle (§ 5.4) |
| Grievance | How often its home state has ruled against it |
| Posture | How its home state has chosen to treat it (§ 4.7) |
| Declared move | A major action announced and counting down, if any |

### 4.2 The turn

- **Yearly turn**, each actor in a fixed month of its own so that the world's
  actors are spread over the year: assess the position, score the goals,
  choose one, choose the verb the actor can afford that serves it best, act.
- **Quarterly step** for the routine tier only: holdings grow or decay,
  currencies accrue, rivalry between holdings in the same place is resolved.
- A goal already held gets a bonus (+15 on a 0–100 score) when re-scored, so
  goals don't flap from year to year.

### 4.3 Three currencies

**Owner**: more than one currency, with political capital and moral authority
beside money. Three, each with its own source and its own uses:

| Currency | Scale | Comes from | Buys |
|---|---|---|---|
| **Funds** | money | The actor's income: for a firm, a share of what its owners would have invested | Expansion, campaigns, hired force, bribes, research, welfare, a foundation, a press |
| **Connections** | 0–100 | Years established, its leading character's interest group in government, a favorable posture, the state having backed it, campaign money that backed the winner | Stalling or speeding a law, a petition that is heard, capture of a regulator |
| **Standing** | 0–100 | Its conduct: its foundation (§ 5.5), welfare for its workers (§ 9), no exposures, no blood on its hands | Backing for its petitions, and the price the state pays for acting against it |

- **Funds are real money** (**owner** agreed). A firm's funds are its claim on
  its home country's investment pool. Yearly accrual is 10% of the firm's
  estimated dividends; script cannot read a company's profit, so the estimate
  is the firm's share of the country's building levels times the pool's gross
  income, scaled by prosperity. The claim is capped at five years' accrual.
  When the firm spends funds on anything but construction, that money leaves
  the investment pool, so lobbying has a cost the player can see in the
  economy. Construction the firm starts is ordinary private construction.
- **Conversions are slow and lossy, and each is a wager.** Funds into
  Standing is a foundation (§ 5.5): a holding in a place, which takes years
  to grow and can be tainted. Funds into Connections is campaign money
  (§ 8.3), which pays only if the side it backed wins.
- **Each currency is wanted by unlike verbs.** In one year a firm's funds can
  go to a concession, a campaign, a laboratory or its workers, and its
  Connections to stalling one law, speeding another or holding a regulator.
  The turn picks the verb that serves the goal best, so what a firm does
  with a pound shows what it wants.
- **Attacks aim at a currency.** Exposure of a secret move costs Standing, and
  so does a strike broken by force (§ 9.2). Being forbidden costs
  Connections, and so does backing the loser of an election.
- **Standing sets the state's price.** Every state action against an actor
  (§ 6.6) costs the state in proportion to the actor's Standing: breaking a
  well-regarded firm angers the people and groups who back it, breaking a
  hated one is cheap or even popular.
- A movement-hosted actor would not get a fourth currency for numbers: the
  engine's own support figure is that (§ 15).

### 4.4 Holdings

A **holding** is a position an actor has established that stays until it is
removed. It has a type, a place, a strength from 0 to 100, an upkeep and a
yield. The yield is often a plain modifier, applied by the mod's
dynamic-modifier pattern from one refresh site
(`docs/systems/mod_systems/dynamic_modifier_pattern.md`).

Verbs create, strengthen, attack and defend holdings, and the state's counters
are aimed at holdings too. That contest is what makes a modifier feel like
part of a system (principle 4).

This slice has seven types. A firm holds at most one of each, except
concessions.

| Holding | Where | Yield | Ends when |
|---|---|---|---|
| **Cartel** (§ 6) | The home country, for the firm's sector | Output of the sector restricted, so its price rises; the firm's funds accrue faster | Broken by a court, legislated away, or the firm's share of the sector falls |
| **Captured regulator** (§ 6.4) | The home country | Exposure of the cartel less likely; a case against it weaker | Audited out, or the firm stops paying |
| **Concession** (§ 7) | One state of another country, or of a decentralized nation | Funds to the firm; output of its building type in that state; a stake the home country may be asked to defend | Expelled, abandoned, forbidden, or handed to another protector |
| **Press** (§ 8.5) | The home country | Its own secret moves exposed less often; its rivals' more often; its campaign money goes further | Closed under the speech laws, discredited by an exposure of its owner, or the firm stops paying |
| **Company town** (§ 9.3) | The firm's seat (§ 4.5) | Fewer radicals from its workers' standard of living, and votes that follow the firm; under the harsh kind, wages held down | Broken by a labor law, by the state, or by a strike the firm loses |
| **Laboratory** (§ 10.2) | The firm's seat | Research toward the technologies its sector uses; throughput of its building types at home once strong | Robbed by a rival's espionage, starved of funds |
| **Foundation** (§ 5.5) | One home state | Education access and lower mortality there; Standing | Tainted by an exposure of its founder, or the firm stops paying |

Three of the seven do the country good (the laboratory, the foundation and
the mild company town), which is what gives the Favored posture a payoff
(§ 4.7).

Where each lives in script is § 13.

### 4.5 Presence

There is no per-state table of where an actor is present. Holdings have a
place, and the map and the roster roll them up to state, country or region.
Real building levels stay in the engine and are read, never mirrored.

Script can read how many levels of a building, and how much of a country's
GDP, are owned from a given *country* (`levels_owned_by_country`,
`gdp_owned_by`), and a company's worldwide total (`company_owned_levels`), but
not one company's levels in one state. So a firm's **stake** in a host is its
concessions' strength there plus the levels of its building types owned from
its home country. Two firms of one home in one sector and one host share that
second figure; it is split between them by concession strength.

**The firm's seat.** A company town and a laboratory sit in one home state,
the firm's seat: the incorporated home state with the most levels of the
firm's building types, chosen when the holding is founded and kept while the
state stays in the country. It is derived from the map, not picked by a
player (principle 5). If script can reach a company's headquarters state
(§ 16, probe 11), that state is the seat. A foundation takes the seat too
unless another firm's foundation is there, and then the next state by the
same measure.

Three zoom levels follow abroad from how much is at stake (**owner** asked
whether a second country is then tracked per state):

- **Region**: the firm has a concession somewhere in the strategic region.
  Shown on the map and in yearly roll-ups.
- **Host country**: once a firm has a concession in a country, the record
  keeps its stake there and that government's treatment of it.
- **State**: only the states its concessions sit in.

### 4.6 Three tiers of action

**Owner**: major actions about one in two or three years against the player,
fewer if things go well; minor actions common, in many places at once, most
needing nothing from the player; a player may notice a firm growing powerful
and act before any conflict, but is never required to.

| Tier | Examples | Shown as | Player input |
|---|---|---|---|
| **Routine** | Open or grow a concession, undercut a rival's concession, endow a foundation, fund a campaign, stall or speed a law, pay a regulator, fund research, raise or break its workers | Ledger lines, yearly roll-ups, the map | None |
| **Threshold** | "Controls 40% of its sector", "its stake in Persia has passed £X", "is now strong enough to defy the state", "has put more into this election than any party's own backers", "is failing" | A notification, once per crossing | None; the cue to act early |
| **Major** | A petition to the state (for protection abroad, for a law, for relief), a bid for a monopoly charter, defiance of an order, turning to another protector | A declared move with a six-month countdown (**owner**: one length for every move, so the alert means the same thing each time), a top-bar alert, an event at the end | An answer, or the posture's default |

- Major moves come from grievance or opportunity, never from a timer, so a
  well-run country sees few. A cap sits underneath as a safety net: one
  declared move at a time per country against its own government, and none
  within a year of the last.
- **The widened firm does not raise that budget.** There are more kinds of
  major move now, and the cap is the same, so they queue. When two firms
  would declare in the same year the one with the higher goal score goes
  first, and the other re-scores at its next turn. The new chains add mostly
  routine moves, which is where the owner wanted the world to be busy.
- **Secrecy**: a routine move may be secret (a cartel formed, a bribe paid, a
  concession kept open against orders). Its *effect* is always visible (the
  price rose) and the ledger shows it with the author unknown until it is
  exposed. A major move is always declared.
- **Exposure** at home comes from the speech laws, the policing and Home
  Affairs institutions, the courts and the pressure of rival actors. Abroad
  it comes from the host's counterintelligence, which the Covert Warfare
  system already scores.

### 4.7 Posture

The home state sets one posture per actor, from the tab. It is the standing
answer to that actor and replaces most clicking (principle 10).

| Posture | Default answer to a petition | Effect on the actor |
|---|---|---|
| **Favored** | Grant: Back (§ 7.4), Take it up (§ 8.4), Rescue (§ 11.2) | Connections accrue faster; it weighs the state's aims in choosing where to act; rival actors' Standing with the state falls |
| **Tolerated** (default) | Stand aside | None |
| **Restrained** | Refuse: Forbid, Refuse, Let it fail | Connections accrue slower; routine moves abroad cost it more; Grievance rises by one every five years |

Every petition has the same three shapes of answer, so a posture means the
same thing whatever is asked. Only a refusal is a ruling against the firm
and raises Grievance.

**What Favored buys the state.** A Favored firm aims its constructive
holdings where the state is: its laboratory works toward the technology the
country is researching before its own choice (§ 10.2), and its foundation
goes to the state with the lowest literacy in place of its seat. The price
is the default answers above and a firm that grows faster.

An AI state's posture is derived (§ 12.1).

## 5. Firms

### 5.1 Which companies, and their sector

Every company in every country is a firm, vanilla's and the mod's, flavored
and generic. Nothing is added to `common/company_types/`.

A generator in the usual pattern (config in, generated script out, run on
reload) reads each company type's building types and writes, per type: its
building types, the goods they make, and their two largest input goods by the
base production methods. That table is the firm's **sector**. A hand-written
config beside it lists which laws burden which sectors (§ 5.2, goal 4).

A firm's **share** of its sector is its owned levels over the country's levels
in its building types. Its owned levels are worldwide, so a firm with much
abroad reads a little high; acceptable for a first build, and noted in the
tab's tooltip.

### 5.2 Eight goals

**Owner** approved the first five, then the widening to eight. Each is scored
0–100 from readouts script already has; the highest is the firm's goal, shown
with its reason.

| Goal | Scored from | Pursued by |
|---|---|---|
| **Cheaper inputs** | Home market price of its input goods above base | A concession where the good is made (§ 7); pressing a cartel that sells it (§ 6.3); a lower tariff on the good (§ 8) |
| **A protected market** | Home market price of its output below base while the market imports it | A cartel (§ 6); a tariff on its output, by campaign money and petition (§ 8) |
| **Security of its assets abroad** | Trouble at its concessions (§ 7.3) | Bribes, hired force, a friendlier government in the host (§ 8.6), a petition for protection |
| **A friendly law** | The law table (§ 8.1): a law in force or being enacted that burdens its sector, or one within reach that would favor it | The politics chain (§ 8) |
| **Dominance** | Its share of the sector; a rival country's firm in the same region | A cartel, a monopoly charter, out-building the rival's concession |
| **Labor peace** | Radicals and turmoil at its seat; a labor law being enacted; vanilla's Strike entry (`je_strike`) active | Welfare, strikebreaking, a company town (§ 9) |
| **A technical lead** | A technology its sector uses that the home country lacks and can research, more if a rival firm's country has it | Research, a laboratory, espionage (§ 10) |
| **Survival** | Low and falling prosperity, and the months the mod's failing-company rule has counted against it; the Banking Cycle in downturn or panic; a law removing its buildings or ending private ownership | Retrenchment, a petition for relief (§ 11) |

A friendly law covers seeking a law as well as blocking one.

All eight are computed and shown for every firm from the first build, since a
visible goal is most of what makes an actor legible. What the eight give that
the five did not:

- **A weak firm has a goal.** Four of the first five were offense. Survival
  outranks everything else for a failing firm, and Labor peace for one whose
  seat is in turmoil.
- **Firms point at each other.** Cheaper inputs and A protected market are
  opposite stances on the same tariff, held by the firms that buy a good and
  the firms that make it. A friendly law sets sectors against each other
  wherever the law table gives them opposite signs.
- **Some goals do the country good.** A technical lead is pursued by research
  the country keeps.

### 5.2a Scoring, so that goals change

- A goal's score is its **pressure** (the readout in the table, 0–100) times
  a **weight** from temperament (§ 5.3) and condition (§ 5.4), each between
  0.5 and 1.5.
- A goal the firm has no verb for under the present laws scores 0, as
  Dominance does under Command Economy (§ 6.2).
- Survival's pressure is 0 for a prosperous firm and passes 80 only when
  prosperity is low and falling, so it interrupts and does not linger.
- The +15 for a goal already held (§ 4.2) stays.
- The ledger records a change of goal with the readout that caused it ("coal
  is 40% above base", "the Factory Acts are being enacted").

### 5.3 Temperament: the executive

A company has an executive, a character with an ideology, traits, a culture
and an interest group. The executive is the firm's temperament (principle 6):

- **Boldness** (§ 7.5): raised by ambitious and reckless traits, lowered by
  cautious ones.
- **Attachment to home**: high when the executive's culture is a primary
  culture of the home country; lowered by a cosmopolitan or radical ideology.
- **Taste for force**: a jingoist executive petitions for armed protection and
  hires force readily; a pacifist or humanitarian one bribes or abandons.
- **Connections**: accrue faster while the executive's interest group is in
  government.
- **Paternalism**: an executive with a reforming, humanitarian or religious
  ideology answers labor trouble with welfare and endows a foundation early;
  a market-liberal or authoritarian one breaks strikes (§ 9.2).
- **Politics**: the executive's interest group is the side the firm's
  campaign money goes to when the law table gives no reason to prefer
  another (§ 8.3).

The table of traits and ideologies is built from the real lists at build time.
A change of executive changes the firm's behavior, and the ledger says so.

### 5.4 Condition: how the firm is doing

Temperament is who runs the firm. Condition is the state it is in, and it
shifts the goal weights of § 5.2a.

| Reading | From | Effect |
|---|---|---|
| **Prosperity** | The company's own prosperity and its weekly change, both readable (§ 16) | Prosperous: Dominance and A technical lead weigh more, and Boldness (§ 7.5) rises. Low and falling: Survival's pressure rises, and funds accrue slower |
| **The business cycle** | The Banking Cycle's phase, when that rule is on | Boom: the expansion goals weigh more and concessions open faster. Downturn or panic: Survival and A protected market weigh more, and every firm's funds accrue slower |
| **Exposure to trade** | Whether the home market exports or imports its output and its inputs | Sets the sign of its stance on the trade laws and on each tariff (§ 8.1) |

With the Banking Cycle rule off, the cycle row reads as neutral.

### 5.5 The foundation: Standing as a holding

History: Carnegie's libraries, the Rockefeller Foundation, the Wellcome
Trust, Tata's institutes, the Krupp and Cadbury schools.

Standing does not come from a plain conversion of funds. It comes from a
holding, so that a firm's good name has a place and can be attacked
(principle 4).

- **Founding.** A firm with funds to spare and Standing under 60 endows a
  foundation: a founding cost, then upkeep. Strength grows 5 a year.
- **Yield.** At strength 100, in its state: education access and lower
  mortality (`state_education_access_add`, `state_mortality_mult`, in
  proportion below that), and for the firm 2 Standing a year, up to a
  Standing equal to the foundation's strength.
- **Taint.** When a secret move of the firm is exposed, the foundation loses
  20 strength as well as the firm its Standing: the gift now looks like
  cover. A strike broken with blood (§ 9.2) does the same.
- **The state's price.** A foundation is why acting against a well-regarded
  firm costs something: § 6.6's costs scale with Standing, and the state
  cannot take a foundation, only wait for its founder to fall.
- **It outlasts the cause.** A foundation whose firm stops paying decays 5 a
  year, and its yield with it, so a broken firm's schools close slowly and
  the state can see that coming in the firm's row.

## 6. The domestic chain: the trust

History: Standard Oil, the Rhenish-Westphalian Coal Syndicate, the zaibatsu,
De Beers. The chain runs on the mod's existing antitrust law group (Antitrust
& Market Structure, `lawgroup_antitrust` in `common/laws/extra_laws.txt`) and
its National Champion Exemption amendment, which today are flat modifiers.
This gives them something to govern.

### 6.1 Stages

1. **Routine.** The firm builds in its sector with its funds and banks
   Connections and Standing.
2. **Threshold.** At 40% of its sector the home state is notified: this firm
   could soon restrict the market.
3. **Cartel.** At 50% a firm whose goal is Dominance or A protected market
   forms a cartel. Whether that is open or secret depends on the law (§ 6.2).
   Strength grows 10 a year up to the firm's share.
4. **Rents.** At strength 100 the sector's throughput in the country is cut by
   20%, in proportion below that. Supply falls, the market price rises, the
   firm's funds accrue faster (up to double). Buyers of the good pay more and
   so do pops.
5. **Reaction.** Other actors and the state respond (§§ 6.3 to 6.6).
6. **Outcome.** The cartel is broken, taxed, chartered as a legal monopoly, or
   entrenched behind a captured regulator.

### 6.2 What each antitrust law means for a cartel

| Law | Cartel | Regulator to capture |
|---|---|---|
| Guilds and Chartered Monopolies | Legal and open; monopoly charters may be petitioned for | None |
| Freedom of Contract | Legal and open; strength grows 15 a year | None |
| Antitrust Enforcement (`law_trust_busting`) | Illegal, so formed in secret; exposure brings a case (§ 6.6) | Yes |
| Regulated Utilities | Illegal in infrastructure and utility sectors, legal elsewhere but capped at strength 40 | Yes; capture raises the cap toward 80 |
| Dirigiste Policy (`law_dirigisme`) | Legal and open for a Favored firm only; others as Antitrust Enforcement | Yes |
| Command/Cooperative Economy | None; the Dominance goal scores 0 | None |

### 6.3 Buyers as actors

A firm whose input good is the cartel's output has Cheaper inputs as a goal,
pointed at the cartel. It acts without being asked:

- **Routine**: pays for exposure (funds; raises the yearly chance the cartel is
  exposed; its press, if it has one, does this for nothing), and gives
  campaign money to the side that favors antitrust (§ 8.3).
- **Major**: petitions the state to bring suit or to change the antitrust law
  (§ 8.4). Taken up, it spends Connections to speed the law's enactment.

Where no company buys the good, nothing speaks for the buyers but the pops who
pay the price, through the engine's own standard of living, radicals and
movements. § 15's industry associations are the later answer.

### 6.4 The trust defends itself

The first two are the politics chain's verbs (§ 8.3), used here in the
cartel's defence.

- **Stall the law.** While a law that would outlaw its cartel is being
  enacted, the firm spends 20 Connections for one enactment setback, at most
  once a year. The ledger names it.
- **Campaign money.** It spends funds for the side whose interest groups
  oppose the law.
- **Capture the regulator.** Under a law with a regulator, it pays 10
  Connections a year to build a Captured regulator holding, 8 strength a
  year, half again as fast under `law_contracted_administration` or
  `amendment_spoils_system`. The holding cuts the cartel's yearly exposure
  chance and a case's chance of success in proportion to its strength. It
  decays 5 a year unpaid. Secret.
- **A foundation.** Funds into Standing (§ 5.5), to raise the state's price
  for moving against it.
- **A press.** It keeps the cartel out of the papers (§ 8.5).

### 6.5 The petition for a charter

A cartel at strength 80, under a law that allows monopolies, or any cartel of
a Favored firm, declares a major move: it asks for a monopoly on its building
type. Granted, the engine's own monopoly applies (`add_company_monopoly`), the
cartel becomes open and permanent, and the firm's Connections rise. Refused,
its Grievance rises by one.

### 6.6 What the state can do

Each is a button on the firm's row, with a cost in proportion to the firm's
Standing (interest-group approval of its backers, and radicals in its states,
bounded by principle 3):

| Action | Needs | Does |
|---|---|---|
| **Inquiry** | Nothing | For a year, +30% to the exposure chance of the firm's secret holdings |
| **Bring suit** | An exposed cartel, or an open one under a law that forbids it | A twelve-month case. Success rises with Judicial Independence and falls with the firm's Connections and its captured regulator. Won: the cartel is removed and cannot re-form for ten years. Lost: it is immune from suit for ten years |
| **Audit the regulator** | A regulator under the law | An exposure roll on the Captured regulator; removes it or cuts it by 20 |
| **Levy on rents** | An open cartel | The treasury takes a share of the rents; the firm's Grievance rises |
| **Grant a charter** | A law that allows monopolies | § 6.5 without waiting to be asked |
| **Change the law** | The usual enactment | § 6.2; the trust contests it (§ 6.4) |

### 6.7 Ties to other systems

- **Markets**: the price rise is the engine's own, from reduced supply.
- **SoL Expectations**: a cartel in a consumer good moves pops' standard of
  living against their expectations.
- **Law enactment and elections**: setbacks, phases and party momentum, all
  with engine effects.
- **Judiciary**: Judicial Independence decides cases; a case is the kind of
  thing the landmark-case events already present.
- **Amendments**: National Champion Exemption makes a Favored firm's cartel
  immune from suit; "Too Large to Break" (`amendment_petition_events.4`)
  should be raised by the largest cartel's firm, not at random.
- **Bureaucracy laws**: decide how fast a regulator is captured.
- **Tax Code**: the levy on rents is an instrument there when that rule is on.
- **Demographics**: cartel rents feed Wealth Concentration's economy term.

## 7. The foreign chain: pulled abroad

History: the Niger and South Africa companies, the scramble for African
territory behind private footholds (**owner**'s example), the Persian and
Chinese concessions, United Fruit, Anglo-Persian. Later the same loop can run
on seabed licences and space colonies.

### 7.1 The concession

A firm whose goal is Cheaper inputs or Dominance opens a **concession** in a
state of another country that makes its input good or buys its output. It does
not ask its government. Opening costs funds. In keeping with soft caps,
nothing forbids a site, but the cost doubles for each of: a home country with
no interest tier in the region, a host of equal or higher rank, a host on bad
terms with the home country. It halves for an unrecognized host and for a
subject or bloc partner of the home country.

**A concession builds its home country's Involvement in the region**
(**owner**: interests come from Involvement, and script can add it). Each
quarter a concession adds Involvement in its strategic region in proportion
to its strength, through `add_involvement`. So a firm's activity raises its
country's interest tier in a region the government never chose, and with the
tier come the claims, plays and rivalries the engine hangs on it. This is the
chain's main lever on the state, and it works with no event at all: the
player opens the diplomatic map and finds the country Engaged in the Niger
basin because a company is.

Two kinds of host:

- **A weaker country** (informal empire). The concession raises output of the
  firm's building type in that state and pays the firm funds. Where the home
  country has investment rights, it grows faster and the engine's own foreign
  investment follows.
- **A decentralized nation** (the frontier). The concession is a trading
  foothold. It pays the firm funds and speeds any colony its home country
  grows in that state region.

Strength grows 5 a year. At most two concessions sit in one state, so two
firms can contest it.

### 7.2 Rivalry

Two concessions of different home countries in one state or one state region
are rivals. Each quarter the stronger firm (funds spent, Standing with the
host, its home's interest in the region) takes strength from the weaker. Both
home countries see it in the ledger, and it lowers relations between them a
little each year it lasts. This is commercial friction before any government
has acted.

### 7.3 Trouble

Each concession has **Trouble**, 0–100. It rises with:

- turmoil and radicals in its state;
- a host law or government hostile to foreign property;
- a rival concession (§ 7.2);
- a firm of the host's own with A protected market as its goal, which presses
  its government to expel the foreigners (the host's mirror of this chain);
- native resistance, in a decentralized nation.

The firm lowers it by itself, as routine moves: **bribes** (funds; secret;
exposure by the host's counterintelligence costs Standing in both countries),
**hired force** (funds and Standing; a chance each year of an incident
that gives the *home country* infamy with the host as victim), and **a
friendlier government**: campaign money for the side in the host that is
least hostile to foreign property (§ 8.6).

A host government may also declare a major move of its own: **Expel the
concession**, with the usual countdown, at a cost in relations with the home
country.

### 7.4 The petition

At Trouble 60, or when the host declares an expulsion, the firm declares a
major move at home: a petition for protection. Its executive's interest group
and any Favored status add weight. **Owner**'s three answers:

| Answer | The state | Then |
|---|---|---|
| **Back** | Commits. The state adds Involvement of its own in the region, a large step at once. Against a country: a guarantee (Trouble −30, relations with the host −20) and a pledge for ten years. If the concession is lost while pledged, the state either acts within two years (a play for investment rights, an open market or a protectorate, at reduced infamy) or loses prestige and every firm's trust. Against a decentralized nation: it starts a colony there outright (**owner**), or speeds one the country is already growing | The firm's Connections rise; it will ask again |
| **Stand aside** | Commits nothing and forbids nothing. Letting the countdown run out is this answer | The firm carries on at its own risk: bribes, force or abandonment by its funds and temperament. The state may inherit the result: an incident in its name, or a foothold it never chose |
| **Forbid** | Orders it out: the concession closes, the Involvement it built is taken back, relations with the host improve | Connections −30, Grievance +1, its backers' approval falls, and the firm picks a response from § 7.5 |

Only Forbid is a ruling against the firm, so only Forbid opens the ladder.

**Back on the frontier starts the colony** (**owner**). The state does not
have to open the colonization lens and pick the state itself: backing the
firm is the decision to colonize. Two things follow. A Favored firm's
default answer is Back, so a countdown left to run out plants a colony; the
alert and the event say so in those words. And an AI state that answers
Back colonizes where its firm is, which is the scramble this chain is meant
to produce. Whether script can start a colony in a named state region, and
whether one started that way grows in a country whose law has no colonial
affairs, is probe 5; the fallback is the growth modifier.

### 7.5 After Forbid: the ladder

**Owner**: a forbidden firm may turn to another power, but not often, and it
must follow from who the firm is.

The firm's **Boldness** is scored 0–100:

- up with its strength against the state (its share of the country's levels,
  its funds against the treasury);
- up with Grievance, 10 a point;
- up or down with the executive's temperament (§ 5.3);
- down with Attachment to home (the executive's culture, the share of its
  assets at home);
- down with the state's reach (naval power and its interest tier in the
  concession's region; a state that can punish it there is obeyed).

| Rung | Boldness | What happens | Tier |
|---|---|---|---|
| 1. Comply | any | The concession closes | Routine |
| 2. Stay quietly | 30 | The concession stays at half strength, in secret. Exposed, it embarrasses the home country with the host | Routine, secret |
| 3. Defy openly | 55 | The concession stays. The state must enforce (a suit to dissolve the firm's holdings) or carry a loss of authority, as a modifier that lasts exactly as long as the defiant concession stands (**owner**), and every other firm's Boldness rises | Major |
| 4. Seek a protector | 75 | The firm asks another power to take the concession under its flag | Major |

A firm takes the highest rung its Boldness allows, with a strong weight
toward the lower ones. A fifth rung, moving its seat abroad, is deferred.

**Who can be the protector.** A country with an interest tier in the region
that is not at war with the home country, not its rival, and not on poor relations
with it. Allies, bloc partners and friendly neutrals weigh highest. If none
qualifies the rung is closed. The candidate is asked (a player by event, the
AI by weight) and may decline.

**The countdown is visible to the home country**, which may:

- **Reverse**: Back the firm after all, at a cost in prestige and authority;
- **Compensate**: pay the firm from the treasury, clearing the Grievance;
- **Let it go**: the concession passes under the protector's flag. The
  protector takes its yield, its petitions and the Involvement it builds from
  then on; the firm stays a company of its home country; relations between
  the two countries fall.

### 7.6 Ties to other systems

- **Interests**: concessions and Back build Involvement, so the engine's own
  interest tiers carry the consequences
  (`docs/vanilla/vanilla_diplomacy_reference.md` § 6; the Involvement the
  mod's treaty articles build is in `docs/systems/mod_systems/treaties.md`).
- **Plays and colonization**: Back resolves into the engine's own plays and
  colonies, never a new kind of war.
- **Decolonization**: the independence nationalization event
  (`decolonization_events.15`) should close or trouble concessions in the new
  country, and their firms should petition.
- **Treaties**: investment rights speed a concession. A later article could
  protect concessions by name.
- **Power blocs**: a bloc partner is a cheap host and a likely protector.
- **Covert Warfare**: the host's counterintelligence exposes bribes; a later
  operation could be funded by a firm.
- **Global Commons and Space Race**: seabed licences and off-world colonies
  are the same loop with a different place, left as hooks.

## 8. Politics at home: the lobby

History: the Anti-Corn Law League against the landed interest, the railway
interest in Parliament, Mark Hanna's campaign of 1896, Hugenberg's papers and
the Ruhr's money, the Navy League's backers, the oil and tobacco firms'
decades of manufactured doubt. Science fiction's version is the senator who
sits for a company.

The chain runs on vanilla's enactment and elections and on the mod's
Electoral Finance law group (`lawgroup_electoral_finance`), which today is
flat voting-power modifiers. This gives it something to govern, as § 6 does
for antitrust.

What it adds that the other chains lack: **firms on opposite sides.** An
election or a law stops being the state against one firm and becomes a
contest between named firms that the state can read and weigh.

### 8.1 The law table

§ 5.1's hand-written config, now signed. For each law it covers, it says
which firms the law **burdens** and which it **favors**, and how much (1 or
2). A firm's stance on a law is the sum over its sector.

| Law group | Burdens | Favors |
|---|---|---|
| Trade policy, and each good's tariff | By exposure to trade (§ 5.4): protection burdens firms that export their output or import their inputs | Firms whose output the market imports |
| Labor Rights, Children's Rights, Labour Associations (vanilla), Ministry of Labor | Firms by how many people a level of their buildings employs (generated from the base methods): the protective laws | The restrictive laws and a Pro-Capital ministry |
| Antitrust | § 6.2 | § 6.2 |
| Resource Transition | Coal, oil and fossil power under the moratorium and the phaseout | None in this slice |
| Automation Policy | Firms whose building types have automated methods, under the Robot Tax and Human Labor Quotas | The same firms under Unrestricted Automation |
| Intellectual Property | § 10.3 | § 10.3 |
| Financial Regulation | Financial firms under the stricter laws | Financial firms under the looser |
| Economic System (**owner**) | Every private firm at weight 2 under Command Economy and Cooperative Ownership, which end private ownership; manufacturers under Industry Banned, Extraction Economy, Agrarianism and Traditionalism | Every private firm under Laissez-Faire; farms and plantations under Agrarianism; mines and wells under Extraction Economy; firms in the sectors it subsidizes under Interventionism |
| Electoral Finance | Every firm, in proportion to what it has spent on campaigns, under Donation Limits and Publicly Funded Elections | Every such firm under Unregulated Donations |

- Tariffs are derived from the market, never hand-written: a firm wants a
  tariff on a good it makes and the market imports, and none on a good it
  buys.
- A test holds the table: every law in a covered group has a row or a
  written reason to have none, so a new law can't slip past it.
- **The economic system is the one law every firm has a stake in**, so its
  enactment is where firms line up most plainly: nearly all of them against
  Command Economy or Cooperative Ownership, industry against agriculture
  over Agrarianism. Once one of those two is in force a firm scores only A
  friendly law (its repeal) and Survival, holds no cartel (§ 6.2), and its
  funds stop accruing, since the private investment it draws on is gone.
  That last point is a first reading; check what the investment pool does
  under each law before building.
- Groups left out here (taxation, welfare) are added when a build shows
  firms have nothing to say about a law they obviously would.

### 8.2 Sides

For the law being enacted, and at each election, every firm has a stance
from the table: for, against or none, with a weight. Firms on one side are
not an alliance and sign nothing. Their spending adds up, and the tab shows
it: this law, these firms for, these against, what each has put in.

- A firm with **A friendly law** as its goal spends on its side every turn.
- A firm with another goal spends only on a stance of weight 2, and half as
  much.
- When a law's enactment ends, every firm that spent on the winning side
  gains 5 Connections and every firm on the losing side loses 5. Lobbying
  is a wager, like campaign money.

### 8.3 Routine verbs

| Verb | Costs | Does | Limit |
|---|---|---|---|
| **Stall** | 20 Connections | One enactment setback on a law it is against (`add_enactment_setback`) | Once a year a firm; one setback a year a law from all firms together |
| **Speed** | 20 Connections | Progress on a law it is for (`add_law_progress`, 10 points of the current checkpoint) | The same |
| **Campaign money** | Funds | Support for the side that favors its law, or its executive's interest group when it has no law at stake | Capped by the Electoral Finance law (below) |

**Campaign money has two forms**, because most of the world in 1836 holds no
elections:

- **Where the country votes**: momentum for a party during the campaign
  (`add_momentum`, which the mod's election events already use). The party
  is the one whose interest groups stand best on the firm's law
  (`law_stance`).
- **Where it does not, or outside a campaign**: patronage. The interest
  group that favors its law gains political strength
  (`interest_group_ig_<group>_pol_str_mult`), as a country modifier scaled
  from all firms' patronage for that group and capped at 20%. It is
  refreshed from one site (§ 13) and decays over three years once the money
  stops.

Either way the money leaves the investment pool (§ 4.3). If the side it
backed is in government after the election, or when the patronized group
enters government, the firm gains 10 Connections. If not, it loses 5.

**What each Electoral Finance law means for campaign money:**

| Law | Campaign money |
|---|---|
| No Campaign Finance Laws (a country without a vote) | Patronage only. Open and uncapped |
| Unregulated Donations | Open and uncapped |
| Donation Limits | Open up to a cap for each firm (1% of the country's yearly investment-pool income). Above it the firm may go on in secret; exposed, it loses 10 Standing and what the excess bought |
| Publicly Funded Elections | Illegal. In secret only, at half effect; exposed, it loses 15 Standing and 10 Connections |

The threshold notice of § 4.6 fires once in a campaign when firms together
have added more momentum to a party than a medium vanilla event would.

### 8.4 The petition for a law

A firm with a goal score of 70 or more, 40 Connections, and a law or a
tariff that would serve the goal declares a major move: it asks the state
for it. Cheaper inputs asks for a lower tariff on its input, A protected
market for a tariff on its output, A friendly law for a law from the table,
Labor peace for a labor law (§ 9).

| Answer | The state | Then |
|---|---|---|
| **Take it up** | Pledges. For a tariff: sets it now and keeps it five years. For a law: begins enacting it within two years | The firm speeds the law for nothing while it is enacted and backs the government's side at the next election. A pledge broken counts as a refusal |
| **Stand aside** | Promises nothing | The firm goes on with its routine verbs, and asks again no sooner than five years |
| **Refuse** | Rules against it | Grievance +1, Connections −10. Each firm on the other side gains 5 Connections: the state took its part |

- The declared move names the firms on the other side, and during the
  countdown each of them may spend Connections against it. For an AI state
  that spending moves the weight of its answer (§ 12.1). A player sees who
  is for and who is against before answering.
- A refused firm does not climb § 7.5's ladder: that is for a forbidden
  concession. Its Grievance feeds Boldness all the same, so a state that
  refuses a firm at home finds it harder to command abroad.

### 8.5 The press

History: Hearst, Northcliffe, Hugenberg, the company papers of every mining
district.

A firm with funds to spare, and either a secret holding to hide or a law at
stake, founds a **Press**: a founding cost, then upkeep. Strength grows 8 a
year. At strength 100, in proportion below that:

- the yearly exposure chance of its own secret moves is cut by 30%;
- that of firms on the other side of its law, and of a cartel that sells
  its input, is raised by 30%;
- its campaign money counts for a quarter more;
- an exposure costs it half the Standing.

Several firms' presses in one country work against each other, so the
effects net out between sides. That is the intended picture: two papers,
two owners, two stories.

| Speech law | The press |
|---|---|
| Outlawed Dissent | None may be founded, and one that exists closes |
| Censorship | Allowed for a Favored or Tolerated firm. A Restrained firm's press is closed at no cost to the state |
| Right of Assembly, Protected Speech | Free. Closing one takes a suit (§ 6.6's kind of case) |

A press is discredited, losing 30 strength, when its owner's secret move is
exposed after the press denied it.

### 8.6 The same verb abroad

History: United Fruit in Guatemala, ITT in Chile, the oil firms in Mexico
and Venezuela.

A firm with a concession whose Trouble comes from the host's government (a
law or a ruling group hostile to foreign property) gives campaign money or
patronage to the side in the host least hostile to it. It is § 8.3's verb
aimed at another country's parties and interest groups (**owner**: kept in
the first version), with these differences:

- It is always secret.
- The host's counterintelligence exposes it, as it does bribes (§ 7.3).
  Exposed: Standing lost in both countries, relations between them down,
  Trouble +20, and the host may expel the concession at half the usual cost
  in relations.
- It needs Boldness 30, and a firm takes it up only once its state has
  stood aside or not yet been asked.
- The host sees the support in its ledger with the author unknown, and may
  hold an Inquiry (§ 6.6).

It does not run a Covert Warfare operation and needs none. Where the home
country is running Election Interference against the same host, both show
in the host's ledger, as two lines.

### 8.7 What the state can do

| Action | Needs | Does |
|---|---|---|
| **Answer a petition** | A declared move | § 8.4 |
| **Inquiry** | Nothing | § 6.6's, which also raises the exposure chance of secret campaign money |
| **Close the press** | A speech law that allows it, or a suit won | Removes the holding; costs in proportion to the firm's Standing |
| **Change the Electoral Finance law** | The usual enactment | § 8.3's table; every firm that spends is against a tighter law, and they contest it |

### 8.8 Ties to other systems

- **Law enactment and elections**: setbacks, progress and momentum, all with
  engine effects.
- **Electoral Finance and the speech laws**: decide what is open, capped or
  secret.
- **Resource Transition**: the coal and oil firms stall the moratorium and
  the phaseout and back the side against them. Nothing resists those laws
  today.
- **Automation Policy, Intellectual Property, Financial Regulation**: each
  gains firms for and against.
- **Tax Code**: a pledged tariff is set the way the customs sync sets one.
- **Amendments**: a petition event of `amendment_petition_events` that
  touches a firm's law should be raised by the firm with the most at stake.
- **Covert Warfare**: counterintelligence exposes money from abroad.

## 9. The workforce

History: the Lowell mills, Krupp's housing and pensions, Bournville,
Pullman's town and the strike of 1894, Homestead and the Pinkertons, Ford's
five-dollar day and Ford's Service Department, Ludlow. Later: the company
compound, the arcology whose owner is also landlord, grocer and police.

Organized labor as an actor is out of this slice (§ 15). This chain is the
firm's half of that contest, so that labor has something to push against
when it arrives. Until then the workers are the engine's pops: their
radicals, their movements and vanilla's Strike entry.

### 9.1 Labor trouble

**Labor peace** is scored from:

- the radical share and the turmoil at the firm's seat (§ 4.5);
- a labor law being enacted that the law table says burdens it;
- vanilla's Strike entry (`je_strike`) being active in the country.

It is weighted up for a firm whose buildings employ many people a level.

### 9.2 Two answers

Both are routine. Which one a firm takes is temperament (§ 5.3,
Paternalism) and funds: welfare costs more.

| | **Welfare** | **Strikebreaking** |
|---|---|---|
| Costs | Funds every year, by the firm's size | Fewer funds; 5 Standing |
| Does at the seat | Loyalists (`add_loyalists_in_state`); builds a company town of the mild kind | For a year, radicals count for less (a state modifier on vanilla's `strike_suppression` pattern); builds a company town of the harsh kind |
| For the firm | 2 Standing a year | Nothing more |
| Risk | None | 10% a year of **bloodshed**: radicals at the seat (`add_radicals_in_state`), 20 Standing lost, the foundation tainted (§ 5.5), a notification. If the firm is Favored, the Trade Unions blame the government too |

**What the Labour Associations law means for strikebreaking:**

| Law | Strikebreaking |
|---|---|
| Guild System, Combination Acts, Anti-Strike Laws | Legal and open, at half cost |
| Right to Associate | Illegal, so done in secret through hired men. Exposed, it costs 10 more Standing and a case may be brought |
| Corporatized Unions | Not available: the state stands between the firm and its workers. Labor peace is scored at half |
| Factory Councils | Not available, and no harsh town can stand |

This is a first reading of those laws; check each against its modifiers
before building.

### 9.3 The company town

A holding at the firm's seat, of one of two kinds, set by which answer
built it. Strength grows 5 a year while the firm keeps paying.

| | **Mild** (Bournville, Essen) | **Harsh** (Pullman, the coal camps) |
|---|---|---|
| Yield at strength 100 | Fewer radicals and more loyalists from changes in the standard of living (`state_radicals_and_loyalists_from_sol_change_mult`); migration pull; 1 Connection a year, for the votes that follow the firm | Throughput of the firm's building types in the state +10% (longer hours for the same pay); 1 Connection a year |
| Cost to the place | None | Radicals build under it: Labor peace is scored higher each year it stands, so it needs more force to hold |
| Ends or shrinks | The firm stops paying | Capped at strength 40 under Worker Protections or Right to Associate; halved by bloodshed; broken by the state |

A firm may turn a harsh town mild by paying welfare for five years. The
other way takes one broken strike.

### 9.4 What the state can do

| Action | Does | Costs |
|---|---|---|
| **Send troops** | Strikebreaking at the state's hand: no Standing lost by the firm, no chance of the firm's own bloodshed | Trade Unions' approval, radicals at the seat; the Industrialists approve |
| **Arbitrate** | The firm pays a year of welfare whether it would or not, and Labor peace is scored at 0 for two years | 5 Connections off the firm; nothing if it is Favored and agrees |
| **Break the town** | Removes a harsh company town | In proportion to the firm's Standing |
| **Change the labor laws** | § 9.2's and § 9.3's tables | The firms the law burdens contest it (§ 8) |

Vanilla's Strike entry already puts choices to the state. Read it before
building: the firm's verbs must feed that entry's outcome where it is
active, never run a second strike beside it.

### 9.5 Ties to other systems

- **SoL Expectations**: a mild town softens the swing from a fall in the
  standard of living, in the state where the country's industry sits.
- **Labor laws and the Ministry of Labor**: decide which answer is legal.
- **Politics at home**: a firm with Labor peace as its goal lobbies on the
  labor laws (§ 8).
- **Automation Policy**: a firm that has held Labor peace as its goal for
  five years counts double for Unrestricted Automation in the law table.
- **Migration**: a mild town pulls people to its state.
- **Organized labor** (§ 15): its first holding, the union local, sits in
  the same state as a company town and takes strength from it.

## 10. Technology: the laboratory

History: Menlo Park, the dye laboratories of BASF and Bayer, Bell Labs,
General Electric's research laboratory, the licences that rebuilt Japanese
industry, a century of stolen blueprints.

This is the chain where a strong firm is good for the country. It is short:
one reading, three verbs, one holding.

### 10.1 The gap

The sector generator (§ 5.1) also writes, for each company type, the
technologies that unlock a production method of its building types. **A
technical lead** is scored from how many of those the home country lacks
and can research (`can_research`), counted half again for each one held by
the home country of a rival firm (§ 7.2), or by any country when no firm
has a rival.

Script has no technology iterator and no link from a key to a technology,
so the per-technology rules are generated, as covert tech theft's are
(`scripts/generators/gen_covert_tech_theft.py`).

### 10.2 Verbs and the holding

- **Research** (routine). Funds into progress on one of its technologies
  (`add_technology_progress`): the earliest it can research, or the
  country's current research when that is on its list or the firm is
  Favored. So a firm may push a technology the country did not choose
  (**owner**: allowed; it is the plainest sign of a firm with a will). One
  firm adds at most 5% of the technology's cost a year, so one firm is a
  nudge and a country full of them is a second research budget.
- **A laboratory** (holding, at the seat). A founding cost and upkeep;
  strength grows 5 a year, 8 with a Ministry of Science. At strength 100 the
  firm's research counts double, and its building types' throughput in the
  home country rises 5% (it knows how to run what it invented), in
  proportion below that.
- **Espionage** (routine, secret). When a rival firm's country holds a
  technology on its list, the firm pays to steal it: a grant of progress on
  the pattern of covert tech theft's, smaller, and with no operation of the
  state behind it. The target's counterintelligence exposes it, helped by
  the economic covert defense its Intellectual Property law gives. Exposed:
  Standing lost, relations between the two countries down a little. If the
  target's firm in that sector has a laboratory, the theft takes 10 of its
  strength.

### 10.3 What each Intellectual Property law means

The mod's `lawgroup_intellectual_property` is flat modifiers today.

| Law | For firms |
|---|---|
| No IP Protection | A laboratory gives no throughput edge, and A technical lead is weighted at half: what a firm invents, its neighbors copy |
| Traditional IP Protection | As § 10.2 |
| Strict IP Protection | The throughput edge is doubled, and a firm with a laboratory at strength 80 may form a cartel at 40% of its sector, not 50% (§ 6.1): a patent pool |
| Creative Commons, Open-Source Innovation | Research counts a quarter more; no throughput edge |
| State Intellectual Property | A laboratory's research always goes to the state's current research; A technical lead is weighted at half |

So in the law table a firm with a laboratory is for Strict IP Protection,
and a firm behind its rivals with no laboratory is against it. This too is
a first reading, to check against the laws before building.

### 10.4 Ties to other systems

- **Research**: progress the country keeps, named in the ledger.
- **Covert Warfare**: the same counterintelligence and the same grant
  pattern as its industrial espionage; a firm's theft is not an operation
  and holds no slot.
- **The trust**: the patent pool lowers the cartel threshold.
- **The Favored posture**: aims the laboratory where the state is
  researching (§ 4.7).
- **Space Race**: its three private companies add progress through a flat
  prosperity modifier today. A laboratory feeding the space programme is
  left as a hook.

## 11. Relief: the failing firm

History: Overend Gurney left to fail in 1866 and Barings rescued in 1890,
Lockheed's loan guarantee of 1971, Chrysler's of 1979, British Leyland, the
car makers of 2008.

Without this chain every firm is on the attack. With it a firm in trouble
behaves like one, and the state faces the oldest question in industrial
policy.

### 11.1 Retrenchment

A firm whose goal is **Survival** (§ 5.2, § 5.4) stops paying for what it
can live without, in a fixed order: its press, its foundation, its
laboratory, then its weakest concession. Each decays at its own rate, and
the ledger says why. So a slump shows on the map as closing schools and
abandoned footholds, and a rival firm takes the concession a failing one
lets go (§ 7.2). All of it is routine, and none of it needs the state.

Retrenchment ends when Survival is no longer the firm's goal. Holdings that
have not reached 0 grow back.

### 11.2 The petition for relief

A firm whose Survival score has been 80 or more at two turns running, and
that is large enough to matter (5% of the country's building levels, or
Favored), declares a major move. It asks for the form that fits:

- a **tariff** on its output, where the market imports it and the home
  country owns the market;
- a **relief line** otherwise: money from the treasury, paid to the firm at
  its seat for five years.

**The relief line** (**owner**: not vanilla's subsidies; the money goes from
the treasury to the company. The shape below is the designer's proposal for
that, and the owner has not ruled on it).

- **The cost** is a weekly expense in the budget for five years, sized to
  the firm: a share of GDP equal to a fifth of the firm's share of the
  country's building levels, at most 0.5% of GDP a year. It is the mod's
  usual treasury cost (a `country_expenses_add = 1` modifier with a
  GDP-scaled multiplier, joined to the Budget breakdown), with the firm
  named on the line.
- **The money reaches the firm**, in three ways:
  1. Its funds are credited with what the treasury pays, and the investment
     pool with the same sum so that the claim is real (§ 4.3). Retrenchment
     stops at once, because the firm can pay its upkeep again.
  2. At its seat (its headquarters state, § 4.5), the throughput of its
     building types rises 10% while the line runs: the works stay open and
     staffed. Script can't raise a company's prosperity directly, so this is
     how the money shows in the company's own figures. It reaches other
     owners' buildings of those types in that one state, which is far
     narrower than a subsidy across the country (§ 16, probe 12).
  3. The mod's failing-company count for the firm is reset, and an AI
     country does not drop the company while the line runs.
- **In a Banking Cycle panic** the first two years are paid at once.
- **No toggle worth flipping.** The line runs its five years. The state may
  end it early, and that is Let it fail at half strength. If the firm's
  goal stops being Survival before the term is out, the cost stops and the
  rest is never owed.

| Answer | The state | Then |
|---|---|---|
| **Rescue** | Grants it: the tariff kept for five years, or the relief line | Connections +10 and one Grievance cleared. **Every firm's Boldness rises by 5 for ten years**: the state has shown it pays. A second rescue of the same firm adds again. The state may name one term, that the firm give up its cartel or its captured regulator; a firm with Boldness 55 turns the terms down, and that is Stand aside |
| **Stand aside** | Nothing | Retrenchment goes on |
| **Let it fail** | Refuses in public | The firm's holdings halve at once, radicals rise at its seat as it lays off, Grievance +1, and it may not ask again for ten years. **Every firm's Boldness falls by 5 for ten years** |

**What failing means in the end.** This system never removes a company
(§ 2). The mod already has an AI country drop a company that has failed its
monthly test for five years, and a player may dissolve one in the companies
panel. Relief sits in front of that: the petition comes at about the second
year of failing, a Rescue resets the count, and after Stand aside or Let it
fail the count runs on. When a company goes, by either route, its holdings
go with it and the ledger records the end of the firm.

### 11.3 In a slump

In a downturn or panic many firms score Survival at once. § 4.6's cap holds:
one declared move at a time, the largest firm first. The first answer is
therefore read by all the others, which is what the Boldness swing is for.

The Banking Cycle's own rescues (its bailout events between countries, and
its tools for the banks) stay as they are. This chain reads the cycle's
phase and writes nothing to it.

### 11.4 Ties to other systems

- **Banking Cycle**: the phase weights Survival (§ 5.4), and a panic brings
  the first two years of a relief line forward.
- **Resource Transition**: Managed Fossil Phaseout removes coal and oil
  buildings whoever owns them, and its compensation reaches no owner. The
  firms that lose them score Survival and petition, so a Rescue is how the
  owners get paid, if the state chooses.
- **The budget and the Tax Code**: a rescue is a line in the Budget
  breakdown or a tariff set the way the customs sync sets one. The mod's
  own subsidies for AI companies' flagship buildings are untouched.
- **Failing companies** (`ai.md`): the same prosperity test and the same
  counter, so the two never disagree about which firm is failing.
- **Amendments**: "Too Large to Break" (`amendment_petition_events.4`) is
  raised by the largest cartel's firm (§ 6.7); a second rescue of one firm is
  a second cause for it.
- **The trust**: a rescue on terms is a way to end a cartel without a court.

## 12. AI countries

**Owner**: AI governments answer by the same weights, and the player must be
able to see the actors in other countries well enough that what an AI country
does is understandable. Done badly, an ally changing course for reasons the
player cannot see would be worse than no system.

### 12.1 How an AI state plays

- **Posture** is derived: Favored when the executive's interest group is in
  government or the law is Dirigiste Policy; Restrained when that group is
  marginalized or the law is Antitrust Enforcement and the firm holds a
  cartel; Tolerated otherwise.
- **Petitions** are answered by weight, the posture's default first.
  - *For protection abroad* (§ 7.4): shifted by the state's strength against
    the host, its infamy, its pacts with the host and its ruler's ideology.
  - *For a law* (§ 8.4): shifted by the stance of the groups in government
    on that law (`law_stance`), and by the Connections spent for and against
    during the countdown. An AI state that takes up a law starts enacting it
    from script when it is enacting nothing (§ 16, probe 13), so the pledge
    is kept where a player can see it.
  - *For relief* (§ 11.2): shifted toward Rescue by the firm's share of the
    country's building levels and by a solvent treasury, and toward Let it
    fail by debt and by a ruler or government hostile to the firm's owners.
- **State actions** (§§ 6.6, 8.7, 9.4) are taken by weight when a cartel's
  price effect, a firm's Boldness or the turmoil at a firm's seat passes set
  levels.
- Every firm in every country takes its turns whoever runs the country.

### 12.2 Legibility rules

1. **No hidden switch.** An actor never changes an AI government's behavior
   directly. It moves quantities the player can see (Involvement and the
   interest tier it gives, relations, incidents, law enactment, party
   momentum and a group's political strength, research progress, a tariff or
   a relief line in the budget, a declared move), each with the actor named in the tooltip or
   ledger.
2. **Nothing in this slice ends a pact.** The only diplomatic effects are
   Involvement, relations drift from rivalry, guarantees and exposed money
   or theft, incidents, and plays that follow a declared petition.
3. **Declared moves are visible to those they concern**: the home country, the
   host, a candidate protector, and any country with an interest in the
   region that is the rival or ally of one of those. A petition for a law or
   for relief concerns the home country, and any country can read it in that
   country's tab (rule 4).
4. **Any country's actors can be inspected.** National Info already shows the
   mod's tabs for another country; this system's tab is public there.
5. **Attribution after the fact.** A play, an incident or an expulsion that
   came out of this system says so in its notification: who pressed for it
   and why.
6. **An answer abroad.** A player who sees a foreign firm's petition coming
   can act on the firm as well as the government: offer it a concession,
   leave its concession untroubled, or expel it early and take the cost.

## 13. Where it lives in script

Constraints from `.claude/rules/script.md` that shape storage:

- A revolution's winner inherits the loser's variables but no modifiers and no
  lists, so anything that must survive is a variable, and every modifier is
  re-derived by the refresh.
- A system behind a game rule must also end when the rule is switched off
  mid-game: the refresh removes every modifier and the tab hides.

| Thing | Stored on | Notes |
|---|---|---|
| A firm's goal, currencies, Grievance, posture, declared move | The company (companies hold variables) | Cleared from `on_company_disbanded` |
| Cartel, Captured regulator | The company, with the yield as a country modifier keyed to the sector's building types | One refresh site, in the quarterly step |
| Concession | The *state* it sits in: two slots, each with firm, home country, protector, strength, Trouble | A state keeps its concessions when it changes hands, and the new owner inherits the Trouble |
| Press, Laboratory, Company town, Foundation | The company: a strength each, the town's kind, and the state for the three that have a place | Yields are state or country modifiers from the same refresh site. The refresh walks firms and reaches each one's state, so no state is searched. A holding ends if its state leaves the country |
| Patronage | The country: one total per interest group | The political-strength modifier is re-derived from the totals each quarter, and the totals decay |
| Sides on a law | The country: the law, the spending for and against, and the three largest firms on each side | Cleared when the turn finds that law no longer being enacted, which is also when § 8.2's Connections are settled |
| The Boldness swing after a Rescue or a Let it fail | The country: a signed count with a ten-year timer | Read by every firm's Boldness |
| The law table, the technologies of each sector | Generated script, from the config and the sector generator | A stance value per law and a rule per technology, for the firm in scope |
| All states with a concession | One global list, as an index | So the quarterly step never walks every state (`scripting_best_practices.md`, "Script Containers: An O(1) Index Beats Iterating the Pool") |
| The ledger | A ring of the last 20 typed entries per country: date, actor, verb, target, size, author known or not | Expendable; lost to a revolution's winner by design |

Other points:

- **Game rule**: one rule for the whole system, in
  `common/game_rules/extra_game_rules.txt`, following
  `docs/systems/mod_systems/game_rules.md`. **Owner**: default off while
  phases 1 to 6 are being built, as the Tax Code was, and on once the
  play-test list is worked through.
- **Prefix**: the builder's choice, checked with `git grep`; `te_actor_` and
  `te_firm_` already match in the United Nations files.
- **Events**: the petitions and the ends of declared moves, through the
  `add-event` skill; text through the `event-text` skill.
- **Load**: a few hundred companies worldwide late in a game, one yearly turn
  each spread over twelve months, and a quarterly step over the concession
  index and the firms' home holdings. No per-state or per-pop pass. The
  widened firm scores eight goals a turn where it scored five, and the
  technology rules are the long part: gate them behind A technical lead
  being worth scoring at all (a laboratory, or a rival ahead).

## 14. Surface

**Owner**: a journal entry is optional; a tab of the Timeline Extended window
with country variables behind it is enough.

- **A tab** in the Timeline Extended window, named **Private Actors** for
  now (§ 18), bound to a `Country` like the others, so National Info shows
  it for any country
  (`state_and_nation_panels.md` § "Timeline Extended Window Tabs";
  `docs/guides/gui_style_guide.md` before building).
  - **Roster**: one row a firm. Executive, goal and its reason, condition
    (prospering, steady, failing), three currency bars, holdings as chips,
    any declared move with its countdown, the posture control (own country
    only).
  - **Firm detail**: its holdings with strength, yield and Trouble; its eight
    goal scores, each with its pressure and its weights; its stance on the
    law being enacted; the state's actions (§§ 6.6, 8.7, 9.4) with their
    costs.
  - **Politics**: the law being enacted with the firms for and against it
    and what each has spent; at an election, campaign money by party; the
    patronage each interest group holds. Secret money shows as a sum with
    the author unknown.
  - **Ledger**: who did what to whom, newest first, with "author unknown"
    lines for unexposed secret moves.
  - **Abroad**: foreign firms' concessions in this country, and this country's
    firms' concessions elsewhere, by host.
- **A map** of concessions by home country, as an entry in the Map Room
  (`docs/systems/mod_systems/journal_map_modes.md` § "Adding a Map"). At
  home it marks firms' seats, with their company towns, laboratories and
  foundations.
- **Top-bar alerts** on the Space Race pattern
  (`common/alert_types/te_space_race_alerts.txt`): yellow while a declared
  move concerns the country; red when one ends within two months and the
  posture's default is not what the player has set by hand.
- **Notifications** for threshold crossings, once each.
- **Tooltips**: every modifier the system applies names the holding and the
  firm it comes from.
- **Help page** in the window's Help popup, like the other systems'.

## 15. Hooks for later

Kept in the chassis now so that these need no rework:

- **The host is abstract.** A company is one host. A vanilla political
  movement is the second (**owner** raised modelling actors as movements).
  A movement brings support from real pops, selectable by profession,
  culture, religion and the building group a pop works in; pressure on
  interest groups; weight in enactment; agitators as faces; and bolster and
  suppress as ready counters. A movement type can only start the kinds of
  civil war its definition scripts, so one need not be able to revolt. It
  costs: an interest that is a fixed list of law stances, one country only,
  strength counted in people, crowding of vanilla's movements, and exposure
  to Paradox's reworks. So: movements for actors whose power is people, the
  chassis for goals, holdings and verbs.

  | Later actor | Host |
  |---|---|
  | Organized labor | Movement, keyed to the pops working in a sector. Its union local is a holding at a firm's seat that contests the company town (§ 9.5) |
  | Religious organizations (**owner**: conversion, support for co-religionists) | Movement at home; missions abroad as holdings, on § 7's loop |
  | Political movements (**owner**: they have little agency today) | Vanilla's movements, given turns and verbs |
  | Industry associations (**owner**) | Movement keyed to a sector's workers and owners, only where a grievance is live |

- **Every actor has a sector field**, and holdings sit in one registry, so an
  association and a firm in one sector can find each other, and so can
  disagree.
- **Emergent firms**: fragmented sectors with no actor, associations for
  sector-wide interests, a dominant firm where concentration is high, with
  concentration moving of itself. The share readout of § 5.1 and the 40% and
  50% thresholds of § 6.1 are where that would attach.
- **More holdings**: a controlling stake in a rival, a party machine, a
  mission, a union local, a private force.
- **More verbs for firms**: lending and calling loans, capital flight, moving
  the seat abroad, funding a covert operation, licensing a technology to a
  firm abroad.
- **Conquest by a chartered company**: a firm that Stands-aside its way to
  a vanilla company subject. **Owner**: its own spec, after phase 6.
- **The state as customer.** The next goal to add: firms whose output the
  government's own buildings buy (arms, ships, rails, construction) want
  the orders to go on. Their verbs press for rearmament and against
  disarmament treaties, sell to both sides, and fund a war scare through a
  press. It ties to War, to Treaties and to the Nuclear Program Pause, and
  was left out of this slice for that reason alone (§ 2).
- **Vanilla's country lobbies**: a firm with a stake in a country could feed
  the existing pro- and anti-country lobbies there, which vanilla's interface
  already uses to explain a foreign stance (§ 16, probe 4).

## 16. Engine facts

**Known** (source in brackets):

- Companies hold variables; `executive` scopes to a character; regional
  headquarters and owned countries are iterable; prosperity, productivity and
  owned levels are comparable; profit is not readable
  (`scripting_best_practices.md`, "Company AI Fields").
- Building ownership cannot be transferred between owners by script
  (**owner**); production methods can be switched (**owner**;
  `activate_production_method`).
- Effects exist for private construction, enactment setbacks and phases, party
  momentum, creating, bolstering and suppressing movements, appointing an
  executive, company monopolies, incidents, plays, relations and the
  investment pool (`docs/engine/effects_summary.txt`).
- **Money can be taken out of the investment pool** (**owner**):
  `add_investment_pool` takes a negative amount. The mod already does it on
  leaving a monetary union (`te_mon_union_exit_pool_hit`, 2% of GDP, capped at
  what the pool holds). Cap every debit the same way.
- **Script can start a play for any country** (**owner**):
  `create_diplomatic_play` with a type, a target and war goals. The mod does
  it for the wars of independence
  (`common/scripted_effects/decolonization_war_effects.txt`, with a
  self-check that the play exists).
- **Script can add Involvement** (**owner**): `add_involvement = {
  strategic_region = sr:<region> value = N }` in country scope. Vanilla uses
  it once, for 2,500 in a journal entry; the mod not yet. Interest tiers
  follow from Involvement, and `has_strategic_region_interest_tier` reads
  the tier.
- `building_<type>_throughput_add` exists per building type;
  `country_infamy_generation_mult` exists (`vanilla_parsed/common/modifier_types.json`).
- A domestic lobby seeded from history crashes a new game
  (`scripting_best_practices.md`, "Domestic Political Lobbies").
- A company's `prosperity` and `weekly_prosperity_change` are value links,
  and `company_is_prosperous` a trigger (`docs/engine/event_targets_summary.txt`,
  `triggers_summary.txt`).
- `add_momentum` is in party scope and works during a campaign; the mod's
  election events use it. `in_election_campaign` reads the campaign.
  `law_stance` reads an interest group's stance on a law.
- `add_enactment_setback` and `add_law_progress` exist; the mod uses the
  first in events and the second nowhere yet. `start_enactment` starts a law
  from an event option (`events/te_judiciary_events.txt`, guarded by
  `enacting_any_law`).
- `add_technology_progress` adds to any technology whose prerequisites the
  country holds, takes a literal amount only, and there is no technology
  iterator, so rules are generated per technology
  (`scripting_best_practices.md`, "Adding Technology Progress From Script").
- A treasury cost is a `country_expenses_add = 1` modifier applied with a
  GDP-scaled multiplier. The amount is weekly, a re-apply removes the old
  copy first, and a new one joins `gen_budget_breakdown.py`'s sources
  (`scripting_best_practices.md`, "Expense Scaling with GDP").
- The mod counts a company's failing months (prosperity under 10, or too
  small to matter) in the company variable `te_company_months_failing`, and
  an AI country drops the company at 60. Players are exempt
  (`docs/systems/mod_systems/ai.md`, "Failing companies").
- `set_subsidized` is per building, and script can't tell which buildings a
  company owns, which is why relief does not use it
  (`scripting_best_practices.md`, "Subsidy and level levers").
- `set_import_tariff_level` sets one good's level; whether it skips the
  buttons' checks is unverified (`scripting_best_practices.md`, "Dynamic
  Tariff Modifier Pattern").
- These modifiers exist (`vanilla_parsed/common/modifier_types.json`):
  `interest_group_ig_<group>_pol_str_mult` for each of the eight groups,
  `state_education_access_add`, `state_mortality_mult`,
  `state_migration_pull_add`,
  `state_radicals_and_loyalists_from_sol_change_mult`,
  `state_radicals_from_political_movements_mult` (what vanilla's
  `strike_suppression` modifier carries), `country_law_enactment_success_add`.
- Vanilla has a Strike journal entry (`je_strike`), raised by the Trade
  Unions' disapproval and radicals among workers
  (`vanilla_parsed/common/journal_entries.json`).
- The mod's Electoral Finance and Intellectual Property law groups, and
  vanilla's Labour Associations, are flat modifiers with no script reading
  them, so §§ 8 to 10 can give them meaning without colliding with anything.

**To probe in game before the phase that rests on each.** Each ships with the
preferred version and a `TE_SELF_CHECK` line where a wrong guess would be
silent (`CLAUDE.md`, "In-game checks").

| # | Question | Needed for | Fallback |
|---|---|---|---|
| 1 | Does Involvement added by script stay, decay or sit under a cap, and does a negative value take it back? | § 7.1, § 7.4 | Add it once when a concession opens and once on Back, and never take it back |
| 2 | Does a country modifier with `building_<type>_throughput_add` cut every building of the type in the country, and does the price move as expected? | § 6.1, rents | A restricted production method switched in on the firm's buildings |
| 3 | Can a state variable hold a company scope, and what does it read after the company is disbanded? | § 13, concessions | Store the company type and the home country |
| 4 | Can `change_appeasement` on vanilla's existing country lobbies be driven from a firm's stake without the crash? | § 15 | Leave lobbies alone |
| 5 | Can script start a colony in a named state region, and does one started that way grow in a country whose law has no colonial affairs? | § 7.4, Back on the frontier | A colony-growth modifier that applies once the country starts one itself |
| 6 | Do vanilla's play types for investment rights, an open market and a protectorate start cleanly from script with their war goals, as the mod's own independence-war type does? | § 7.4, § 12 | A play type of the mod's own for each |
| 7 | Which executive traits and ideologies are readable from `company.executive`, and does every company always have one? | § 5.3 | Neutral temperament when missing |
| 8 | What happens to a firm's variables and monopoly when its country loses a revolution? | § 13 | Re-seed the firm on the winner's first turn |
| 9 | Does `add_momentum` take effect from a pulse during a campaign, for any party, and for a party of another country? | §§ 8.3, 8.6 | Patronage, the political-strength form, everywhere |
| 10 | Does `add_law_progress` move the current checkpoint from a pulse, and do a setback and progress in one year leave the enactment sound? | § 8.3 | A timed `country_law_enactment_success_add` modifier, as vanilla's strike events use |
| 11 | Can script reach a company's headquarters state? | § 4.5 | The home state with the most levels of its building types |
| 12 | Does a state modifier with `building_<type>_throughput_add` reach that state's buildings of the type and no others? | §§ 9.3, 11.2 | The harsh town and the relief line pay funds to the firm and give no throughput |
| 13 | Does an AI country keep an enactment that script started, or cancel it at its next review? | §§ 8.4, 12.1 | The AI's pledge is only the head start, given when it enacts the law by itself |
| 14 | Does `set_import_tariff_level` from script skip the cooldown and the trade-policy check, and does the level hold against a player's or the AI's own changes? | §§ 8.4, 11.2 | The pledge is the player's to keep by hand; the turn reads the level and counts a lapse as a refusal |
| 15 | What can another system read of vanilla's Strike entry: only that it is active, or its progress and the states involved? | § 9 | Read `has_journal_entry` alone |

## 17. Build order

Each phase is one or more PRs and can be judged in game by itself. Each lands
with tests, its section of a new `docs/systems/mod_systems/` file and index
row, the player guide's coverage (a subsection, since this is a system the
player works through), and its lines in a new play-test list under
`docs/testing/`.

| Phase | Builds | What the owner can judge |
|---|---|---|
| 0 | The probes of § 16, through the `game-qa` skill with the owner's leave | Which fallbacks are needed |
| 1 | Game rule, the sector generator, firm records, goals, currencies accruing, the tab's roster and ledger, National Info. No verbs | Whether firms read as having wants: are the goals and reasons believable for real countries in 1836, 1900, 1950? |
| 2 | The trust (§ 6) with the state's actions and alerts, and the foundation (§ 5.5) | The ten-year test at home |
| 3 | Politics at home (§§ 8.1 to 8.5, 8.7): the law table, sides, stall, speed, campaign money in both forms, the petition for a law, the press | Whether firms disagree with each other: does an election or a law read as a contest between named firms? |
| 4 | The workforce (§ 9), technology (§ 10) and relief (§ 11) | Whether goals change: does a firm in a slump, a strike or a technical race behave differently, and does the Favored posture pay? |
| 5 | Concessions, rivalry, Trouble, the map (§§ 7.1 to 7.3) | Routine activity abroad: is the world busy without being noisy? |
| 6 | Petitions for protection, the three answers, the ladder, campaign money abroad, AI answers and the legibility rules (§§ 7.4, 7.5, 8.6, 12) | Being pulled abroad, and reading an AI country that is |
| 7 | Tuning from play; the AI telemetry probe (`ai.md`) extended to count moves by tier and goals by kind | The noise budget of § 4.6, and whether any goal never wins or always does |

The order changed with the widening. The chains at home come before the
chain abroad, because they prove the chassis (competing goals, firms against
firms, a currency with rival uses) on engine effects the mod already uses,
while the chain abroad waits on most of the probes. Phase 1 computes all
eight goals from the start, so the owner can judge the goals before any verb
exists. Phase 4's three chains are separate PRs and can land in any order.

## 18. Decisions

The owner ruled on all ten on 2026-11-28. Each ruling is written into the
section named, and marked **owner** there.

| # | Question | Ruling | Written in |
|---|---|---|---|
| 1 | The player-facing name. "Interests" collides with vanilla's diplomatic interests and with interest groups | Not "Private Powers". **Private Actors** as the working name, which the owner may yet change; an actor of this slice is a **firm** | § 14 |
| 2 | The game rule's default | Off while phases 1 to 6 are being built, on once the play-test list is worked through | § 13 |
| 3 | The countdown | Six months for every declared move | § 4.6 |
| 4 | Back on the frontier: start a colony, or only speed one? | Start it outright, where script can | § 7.4; § 16, probe 5 |
| 5 | Conquest by a chartered company | Its own spec, after phase 6 | § 15 |
| 6 | Open defiance | A modifier that lasts while the defiant concession stands | § 7.5 |
| 7 | Research the player did not choose | Allowed | § 10.2 |
| 8 | Campaign money abroad in the first version | Kept | § 8.6 |
| 9 | Relief by vanilla's subsidy, which covers every owner's buildings | No. A treasury cost that goes to the company at its headquarters | § 11.2 |
| 10 | Law groups in the first law table | The economic system is included | § 8.1 |

**Still open**

1. **The name.** Private Actors is a working name. It needs settling before
   phase 1's localization, since the tab, the Help page, the alerts and the
   game rule all carry it.
2. **The relief line's shape.** The owner set the direction and left the
   mechanism open. § 11.2 proposes it: a budget line sized to the firm,
   credited to the firm's funds, with a throughput lift at its seat and the
   failing count reset. The part to rule on is the lift at the seat, which
   is the only piece that reaches buildings the firm doesn't own. Without
   it a rescue buys the firm time and keeps its holdings, and does nothing
   for the company's own prosperity.
