# Actors With Interests of Their Own: the Chassis, and Firms as the First Slice

Date: 2026-11-28. From the owner's brainstorm of the same day. The owner set
the principles in § 3, the scope of the first slice (§ 2), the answers to a
petition and the weighting of defection (§ 7), the tiers of action (§ 4.6)
and the rules for AI countries (§ 8); those rulings are marked **owner**.
Everything else is the designer's call, and the owner may revisit any of it
with a stated reason. All numbers are first guesses for the builder to tune.
Nothing here is built. Background: `docs/vanilla/vanilla_politics_reference.md`
§§ 5, 8 and 9, `docs/vanilla/vanilla_diplomacy_reference.md` § 9,
`docs/systems/mod_systems/ai.md` § "Company AI",
`docs/systems/mod_systems/amendments.md`,
`docs/systems/mod_systems/judiciary.md`,
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
3. Two complete chains, one domestic and one foreign (**owner**: narrow but
   deep; few kinds of actor and of action, each tied into other systems and
   legible, so that it reads as part of the world. Breadth comes later).
4. AI countries subject to all of it, with every push on an AI government
   visible and attributed (§ 8).
5. Hooks for the actors that follow (§ 11), and for firms that come into being
   and dissolve with their sector's concentration (the owner's long-run
   direction, out of scope here).

**Non-goals**

- Any actor other than firms: organized labor, political movements, religious
  organizations and industry associations are designed only as far as the
  chassis must allow for them (§ 11).
- Replacing vanilla's company slots, or founding and dissolving companies from
  script.
- Banks' lending verbs, capital flight, takeovers of one firm by another, and
  a firm moving its seat to another country.
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
9. **No hidden switch in an AI government** (§ 8).
10. The design defaults of `CLAUDE.md` hold: soft caps in place of eligibility
    gates, and no setting worth toggling. The player sets a posture and the
    actor plays itself.

## 4. The chassis

### 4.1 The actor

An actor is a record on a **host** scope the engine already has. In this slice
the host is a company; § 11 gives the movement as the second host. The record
holds:

| Field | Meaning |
|---|---|
| Home | The country the host belongs to |
| Sector | The building types and goods it lives on (§ 5.1) |
| Goal | The one aim it is pursuing now, with its reason (§ 5.2) |
| Currencies | Funds, Connections, Standing (§ 4.3) |
| Holdings | The standing positions it has built (§ 4.4) |
| Temperament | Read from its leading character (§ 5.3) |
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
| **Funds** | money | The actor's income: for a firm, a share of what its owners would have invested | Expansion, campaigns, hired force, bribes, charity |
| **Connections** | 0–100 | Years established, its leading character's interest group in government, a favorable posture, the state having backed it | Stalling or speeding a law, a petition that is heard, capture of a regulator |
| **Standing** | 0–100 | Its conduct: jobs and wages in its states, charity, no exposures | Backing for its petitions, and the price the state pays for acting against it |

- **Funds are real money** (**owner** agreed). A firm's funds are its claim on
  its home country's investment pool. Yearly accrual is 10% of the firm's
  estimated dividends; script cannot read a company's profit, so the estimate
  is the firm's share of the country's building levels times the pool's gross
  income, scaled by prosperity. The claim is capped at five years' accrual.
  When the firm spends funds on anything but construction, that money leaves
  the investment pool, so lobbying has a cost the player can see in the
  economy. Construction the firm starts is ordinary private construction.
- **Conversions are slow and lossy.** Funds into Standing is charity (£ per
  point, rising steeply above 60). Funds into Connections is campaign money
  (§ 6.5).
- **Attacks aim at a currency.** Exposure of a secret move costs Standing.
  Being forbidden costs Connections.
- **Standing sets the state's price.** Every state action against an actor
  (§ 6.6) costs the state in proportion to the actor's Standing: breaking a
  well-regarded firm angers the people and groups who back it, breaking a
  hated one is cheap or even popular.
- A movement-hosted actor would not get a fourth currency for numbers: the
  engine's own support figure is that (§ 11).

### 4.4 Holdings

A **holding** is a position an actor has established that stays until it is
removed. It has a type, a place, a strength from 0 to 100, an upkeep and a
yield. The yield is often a plain modifier, applied by the mod's
dynamic-modifier pattern from one refresh site
(`docs/systems/mod_systems/dynamic_modifier_pattern.md`).

Verbs create, strengthen, attack and defend holdings, and the state's counters
are aimed at holdings too. That contest is what makes a modifier feel like
part of a system (principle 4).

This slice has three types:

| Holding | Where | Yield | Ends when |
|---|---|---|---|
| **Cartel** (§ 6) | The home country, for the firm's sector | Output of the sector restricted, so its price rises; the firm's funds accrue faster | Broken by a court, legislated away, or the firm's share of the sector falls |
| **Captured regulator** (§ 6.4) | The home country | Exposure of the cartel less likely; a case against it weaker | Audited out, or the firm stops paying |
| **Concession** (§ 7) | One state of another country, or of a decentralized nation | Funds to the firm; output of its building type in that state; a stake the home country may be asked to defend | Expelled, abandoned, forbidden, or handed to another protector |

Where each lives in script is § 9.

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

Three zoom levels follow from how much is at stake (**owner** asked whether a
second country is then tracked per state):

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
| **Routine** | Open or grow a concession, undercut a rival's concession, give to charity, fund a campaign, pay a regulator | Ledger lines, yearly roll-ups, the map | None |
| **Threshold** | "Controls 40% of its sector", "its stake in Persia has passed £X", "is now strong enough to defy the state" | A notification, once per crossing | None; the cue to act early |
| **Major** | A petition to the state, a bid for a monopoly charter, defiance of an order, turning to another protector | A declared move with a six-month countdown, a top-bar alert, an event at the end | An answer, or the posture's default |

- Major moves come from grievance or opportunity, never from a timer, so a
  well-run country sees few. A cap sits underneath as a safety net: one
  declared move at a time per country against its own government, and none
  within a year of the last.
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
| **Favored** | Back | Connections accrue faster; it weighs the state's aims in choosing where to act; rival actors' Standing with the state falls |
| **Tolerated** (default) | Stand aside | None |
| **Restrained** | Forbid | Connections accrue slower; routine moves abroad cost it more; Grievance rises by one every five years |

An AI state's posture is derived (§ 8.1).

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

### 5.2 Five goals

**Owner** approved the five. Each is scored 0–100 from readouts script already
has; the highest is the firm's goal, shown with its reason.

| Goal | Scored from | Pursued by |
|---|---|---|
| **Cheaper inputs** | Home market price of its input goods above base | A concession where the good is made (§ 7); pressing a cartel that sells it (§ 6.3) |
| **A protected market** | Home market price of its output below base while the market imports it | A cartel (§ 6); pressing the home state through campaign money |
| **Security of its assets abroad** | Trouble at its concessions (§ 7.3) | Bribes, hired force, a petition for protection |
| **Freedom from a regulation** | A burdening law in force or being enacted | Stalling the law, campaign money, capturing the regulator |
| **Dominance** | Its share of the sector; a rival country's firm in the same region | A cartel, a monopoly charter, out-building the rival's concession |

All five are computed and shown for every firm from the first build, since a
visible goal is most of what makes an actor legible. The two chains below give
full verbs to the first, second, third and fifth; the fourth gets the shared
verbs only (stall, campaign money).

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

The table of traits and ideologies is built from the real lists at build time.
A change of executive changes the firm's behavior, and the ledger says so.

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
  exposed), and gives campaign money to the party that favors antitrust.
- **Major**: petitions the state to bring suit or to change the antitrust law.
  Backed, it spends Connections on the law's enactment.

Where no company buys the good, nothing speaks for the buyers but the pops who
pay the price, through the engine's own standard of living, radicals and
movements. § 11's industry associations are the later answer.

### 6.4 The trust defends itself

- **Stall the law.** While a law that would outlaw its cartel is being
  enacted, the firm spends 20 Connections for one enactment setback, at most
  once a year. The ledger names it.
- **Campaign money.** In an election campaign it spends funds for momentum on
  the party whose interest groups oppose the law. Public by default.
- **Capture the regulator.** Under a law with a regulator, it pays 10
  Connections a year to build a Captured regulator holding, 8 strength a
  year, half again as fast under `law_contracted_administration` or
  `amendment_spoils_system`. The holding cuts the cartel's yearly exposure
  chance and a case's chance of success in proportion to its strength. It
  decays 5 a year unpaid. Secret.
- **Charity.** Funds into Standing, to raise the state's price for moving
  against it.

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
nothing forbids a site, but the cost doubles for each of: no home-country
interest in the region, a host of equal or higher rank, a host on bad terms
with the home country. It halves for an unrecognized host and for a subject
or bloc partner of the home country.

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
exposure by the host's counterintelligence costs Standing in both countries)
and **hired force** (funds and Standing; a chance each year of an incident
that gives the *home country* infamy with the host as victim).

A host government may also declare a major move of its own: **Expel the
concession**, with the usual countdown, at a cost in relations with the home
country.

### 7.4 The petition

At Trouble 60, or when the host declares an expulsion, the firm declares a
major move at home: a petition for protection. Its executive's interest group
and any Favored status add weight. **Owner**'s three answers:

| Answer | The state | Then |
|---|---|---|
| **Back** | Commits. Against a country: a guarantee (Trouble −30, relations with the host −20) and a pledge for ten years. If the concession is lost while pledged, the state either acts within two years (a play for investment rights, an open market or a protectorate, at reduced infamy) or loses prestige and every firm's trust. Against a decentralized nation: it starts or speeds a colony there | The firm's Connections rise; it will ask again |
| **Stand aside** | Commits nothing and forbids nothing. Letting the countdown run out is this answer | The firm carries on at its own risk: bribes, force or abandonment by its funds and temperament. The state may inherit the result: an incident in its name, or a foothold it never chose |
| **Forbid** | Orders it out: the concession closes, relations with the host improve | Connections −30, Grievance +1, its backers' approval falls, and the firm picks a response from § 7.5 |

Only Forbid is a ruling against the firm, so only Forbid opens the ladder.

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
- down with the state's reach (naval power and interest in the concession's
  region; a state that can punish it there is obeyed).

| Rung | Boldness | What happens | Tier |
|---|---|---|---|
| 1. Comply | any | The concession closes | Routine |
| 2. Stay quietly | 30 | The concession stays at half strength, in secret. Exposed, it embarrasses the home country with the host | Routine, secret |
| 3. Defy openly | 55 | The concession stays. The state must enforce (a suit to dissolve the firm's holdings) or carry a lasting loss of authority, and every other firm's Boldness rises | Major |
| 4. Seek a protector | 75 | The firm asks another power to take the concession under its flag | Major |

A firm takes the highest rung its Boldness allows, with a strong weight
toward the lower ones. A fifth rung, moving its seat abroad, is deferred.

**Who can be the protector.** A country with an interest in the region that is
not at war with the home country, not its rival, and not on poor relations
with it. Allies, bloc partners and friendly neutrals weigh highest. If none
qualifies the rung is closed. The candidate is asked (a player by event, the
AI by weight) and may decline.

**The countdown is visible to the home country**, which may:

- **Reverse**: Back the firm after all, at a cost in prestige and authority;
- **Compensate**: pay the firm from the treasury, clearing the Grievance;
- **Let it go**: the concession passes under the protector's flag. The
  protector takes its yield and its petitions; the firm stays a company of its
  home country; relations between the two countries fall.

### 7.6 Ties to other systems

- **Interests, plays and colonization**: Back resolves into the engine's own
  plays and colonies, never a new kind of war.
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

## 8. AI countries

**Owner**: AI governments answer by the same weights, and the player must be
able to see the actors in other countries well enough that what an AI country
does is understandable. Done badly, an ally changing course for reasons the
player cannot see would be worse than no system.

### 8.1 How an AI state plays

- **Posture** is derived: Favored when the executive's interest group is in
  government or the law is Dirigiste Policy; Restrained when that group is
  marginalized or the law is Antitrust Enforcement and the firm holds a
  cartel; Tolerated otherwise.
- **Petitions** are answered by weight: the posture's default first, shifted
  by the state's strength against the host, its infamy, its pacts with the
  host and its ruler's ideology.
- **State actions** (§ 6.6) are taken by weight when a cartel's price effect
  or a firm's Boldness passes set levels.
- Every firm in every country takes its turns whoever runs the country.

### 8.2 Legibility rules

1. **No hidden switch.** An actor never changes an AI government's behavior
   directly. It moves quantities the player can see (relations, incidents,
   law enactment, a declared move), each with the actor named in the tooltip
   or ledger.
2. **Nothing in this slice ends a pact.** The only diplomatic effects are
   relations drift from rivalry and guarantees, incidents, and plays that
   follow a declared petition.
3. **Declared moves are visible to those they concern**: the home country, the
   host, a candidate protector, and any country with an interest in the
   region that is the rival or ally of one of those.
4. **Any country's actors can be inspected.** National Info already shows the
   mod's tabs for another country; this system's tab is public there.
5. **Attribution after the fact.** A play, an incident or an expulsion that
   came out of this system says so in its notification: who pressed for it
   and why.
6. **An answer abroad.** A player who sees a foreign firm's petition coming
   can act on the firm as well as the government: offer it a concession,
   leave its concession untroubled, or expel it early and take the cost.

## 9. Where it lives in script

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
| All states with a concession | One global list, as an index | So the quarterly step never walks every state (`scripting_best_practices.md`, "Script Containers: An O(1) Index Beats Iterating the Pool") |
| The ledger | A ring of the last 20 typed entries per country: date, actor, verb, target, size, author known or not | Expendable; lost to a revolution's winner by design |

Other points:

- **Game rule**: one rule for the whole system, in
  `common/game_rules/extra_game_rules.txt`, following
  `docs/systems/mod_systems/game_rules.md`.
- **Prefix**: the builder's choice, checked with `git grep`; `te_actor_` and
  `te_firm_` already match in the United Nations files.
- **Events**: the petitions and the ends of declared moves, through the
  `add-event` skill; text through the `event-text` skill.
- **Load**: a few hundred companies worldwide late in a game, one yearly turn
  each spread over twelve months, and a quarterly step over the concession
  index. No per-state or per-pop pass.

## 10. Surface

**Owner**: a journal entry is optional; a tab of the Timeline Extended window
with country variables behind it is enough.

- **A tab** in the Timeline Extended window, bound to a `Country` like the
  others, so National Info shows it for any country
  (`state_and_nation_panels.md` § "Timeline Extended Window Tabs";
  `docs/guides/gui_style_guide.md` before building).
  - **Roster**: one row a firm. Executive, goal and its reason, three currency
    bars, holdings as chips, any declared move with its countdown, the posture
    control (own country only).
  - **Firm detail**: its holdings with strength, yield and Trouble; its five
    goal scores; the state's actions (§ 6.6) with their costs.
  - **Ledger**: who did what to whom, newest first, with "author unknown"
    lines for unexposed secret moves.
  - **Abroad**: foreign firms' concessions in this country, and this country's
    firms' concessions elsewhere, by host.
- **A map** of concessions by home country, as an entry in the Map Room
  (`docs/systems/mod_systems/journal_map_modes.md` § "Adding a Map").
- **Top-bar alerts** on the Space Race pattern
  (`common/alert_types/te_space_race_alerts.txt`): yellow while a declared
  move concerns the country; red when one ends within two months and the
  posture's default is not what the player has set by hand.
- **Notifications** for threshold crossings, once each.
- **Tooltips**: every modifier the system applies names the holding and the
  firm it comes from.
- **Help page** in the window's Help popup, like the other systems'.

## 11. Hooks for later

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
  | Organized labor | Movement, keyed to the pops working in a sector |
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
  the seat abroad, conquest as a chartered company subject, funding a covert
  operation.
- **Vanilla's country lobbies**: a firm with a stake in a country could feed
  the existing pro- and anti-country lobbies there, which vanilla's interface
  already uses to explain a foreign stance (§ 12, probe 4).

## 12. Engine facts

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
- No effect declares a diplomatic interest; `has_interest_marker_in_region`
  only reads one.
- `building_<type>_throughput_add` exists per building type;
  `country_infamy_generation_mult` exists (`vanilla_parsed/common/modifier_types.json`).
- A domestic lobby seeded from history crashes a new game
  (`scripting_best_practices.md`, "Domestic Political Lobbies").

**To probe in game before the phase that rests on each.** Each ships with the
preferred version and a `TE_SELF_CHECK` line where a wrong guess would be
silent (`CLAUDE.md`, "In-game checks").

| # | Question | Needed for | Fallback |
|---|---|---|---|
| 1 | Does `add_investment_pool` take a negative amount? | § 4.3, funds as real money | A timed modifier on capitalists' investment-pool contribution in the firm's headquarters state |
| 2 | Does a country modifier with `building_<type>_throughput_add` cut every building of the type in the country, and does the price move as expected? | § 6.1, rents | A restricted production method switched in on the firm's buildings |
| 3 | Can a state variable hold a company scope, and what does it read after the company is disbanded? | § 9, concessions | Store the company type and the home country |
| 4 | Can `change_appeasement` on vanilla's existing country lobbies be driven from a firm's stake without the crash? | § 11 | Leave lobbies alone |
| 5 | Can script start or speed a colony in a named state region? | § 7.4, Back on the frontier | A colony-growth modifier that applies once the country starts one itself |
| 6 | Can `create_diplomatic_play` start the three plays of § 7.4 for an AI country with the right war goal? | § 7.4, § 8 | A weight in `common/ai_strategies/` in place of a scripted play |
| 7 | Which executive traits and ideologies are readable from `company.executive`, and does every company always have one? | § 5.3 | Neutral temperament when missing |
| 8 | What happens to a firm's variables and monopoly when its country loses a revolution? | § 9 | Re-seed the firm on the winner's first turn |

## 13. Build order

Each phase is one or more PRs and can be judged in game by itself. Each lands
with tests, its section of a new `docs/systems/mod_systems/` file and index
row, the player guide's coverage (a subsection, since this is a system the
player works through), and its lines in a new play-test list under
`docs/testing/`.

| Phase | Builds | What the owner can judge |
|---|---|---|
| 0 | The probes of § 12, through the `game-qa` skill with the owner's leave | Which fallbacks are needed |
| 1 | Game rule, the sector generator, firm records, goals, currencies accruing, the tab's roster and ledger, National Info. No verbs | Whether firms read as having wants: are the goals and reasons believable for real countries in 1836, 1900, 1950? |
| 2 | The domestic chain (§ 6) with the state's actions and alerts | The ten-year test at home |
| 3 | Concessions, rivalry, Trouble, the map (§§ 7.1 to 7.3) | Routine activity abroad: is the world busy without being noisy? |
| 4 | Petitions, the three answers, the ladder, AI answers and the legibility rules (§§ 7.4, 7.5, 8) | Being pulled abroad, and reading an AI country that is |
| 5 | Tuning from play; the AI telemetry probe (`ai.md`) extended to count moves by tier | The noise budget of § 4.6 |

## 14. Open decisions

For the owner; the designer's lean is given.

1. **The player-facing name.** "Interests" collides with vanilla's diplomatic
   interests and with interest groups. Lean: the tab is **Private Powers**;
   an actor of this slice is a **firm**.
2. **The game rule's default.** Lean: off while phases 1 to 4 are being built,
   as the Tax Code was; on once the play-test list is worked through.
3. **The countdown.** Six months for every declared move. Lean: keep one
   length, so the alert means the same thing each time.
4. **Back on the frontier.** Should Back start a colony outright, where script
   can (probe 5), or only speed one the player starts? Lean: speed only, so
   the state never colonizes by event.
5. **Conquest by a chartered company** (a firm that Stands-aside its way to a
   vanilla company subject). It is the strongest expression of the theme and
   a large piece of work. Lean: after phase 4, as its own spec.
6. **Open defiance.** Rung 3 leaves the state with a lasting loss of authority
   until it enforces. Lean: a modifier that lasts while the defiant
   concession stands, so it has a visible cause and a clear remedy.
