# States and population

The mod changes how people spread across your country and how its states
develop. Crowded states draw fewer migrants, homelands follow the cultures that
actually live in a region, a state's tourism depends on what it offers visitors,
and a government can move settlers onto an empty frontier. The state panel gains
tiles that show most of these. Everything in this chapter is always on except
internal resettlement, which the Internal Resettlement game rule controls (see
the [Introduction](01-introduction.md)).

## State panel additions

The mod adds tiles to the status grid of the state panel and a tourism card
above the grid. Each tile is titled with a game concept you can hover for an
explanation, and its tooltip breaks the numbers down.

<!-- screenshot: a state panel showing the Homeland Dynamics, Arable Land and Migration Crowding tiles and the tourism card -->

| Tile | Shown | What it tells you |
|---|---|---|
| Homeland Dynamics | Always | Which cultures are gaining or losing homeland status here, with a progress bar for each, or why nothing can change. |
| Arable Land | Always | Total arable land, how much technologies and other regional effects add to the geographic base, and the arable-land multiplier. |
| Migration Crowding | While the state is over its crowding threshold | Population, crowding threshold, crowding ratio with a bar, and the migration pull penalty. |
| Solar Collector | Once your country has one | Receiver slots available and generated (3 per staffed level). A megaproject; see [The extended timeline](02-timeline.md). |
| Antimatter Facility | Once your country has one | Engine and warhead-plant slots available and generated (5 per staffed level). |
| UN Mission | While a UN mission works in the state | The mission's type, months, strength and progress; see [The United Nations](09-united-nations.md). |
| Tourism card | Always | Tourism output and throughput from each source, with a bar toward each source's cap. |

## Migration crowding

Every state has a crowding threshold of 10,000 people for each unit of its
geographic arable land, the land the state starts with before technologies add
to it. Once the population passes the threshold, the state carries a Population
Pressure modifier that cuts its migration pull. The modifier is recalculated
once a year.

The penalty starts gently and then climbs fast. Up to ten times the threshold it
grows with the square of the excess; beyond that it adds 10 percentage points
for each further multiple.

| Population against the threshold | Migration pull penalty |
|---|---|
| 1× or less | none |
| 4× | 5% |
| 7× | 20% |
| 10× | 45% |
| 15× | 95% |
| 20× | 145% |

### Raising crowding tolerance

The Migration Crowding Tolerance modifier multiplies the threshold: +50%
tolerance lets a state hold half as many people again before the penalty starts.
The tile's tooltip lists every source, under Urban Capacity.

| Source | Tolerance |
|---|---|
| Ministry of Urban Planning (institution) | +10% per level |
| Highway on the Civil Highway, Electric Civil Highway or Autonomous Highway method | +10% per level, scaled by staffing |
| Modern Skyscrapers, Wireless Internet (Wi-Fi), Autonomous Vehicles, Post-Scarcity Economy | +15% each |
| Modern Urban Planning, Advanced Structural Engineering | +20% each |
| Urban Planning power bloc principle | +25% at tiers I to III, +50% at IV, +100% at V, plus +5% per Ministry of Urban Planning level (+10% at IV, +20% at V) |
| National Park building on National Park, National Forest or National Wildlife Refuge | −5%, −7.5% or −10% per level, scaled by staffing |

Ministries are explained in [Ministries](05-politics.md#ministries). The same
tolerance also raises the densities that open and close a resettlement frontier.

## Dynamic homelands

With the mod, homelands follow population. A primary culture of yours that makes
up enough of a state's people can gain a homeland there, and a culture that is
not primary and has dwindled can lose one. Each change fills its own progress
bar over years, with no random rolls. A completed change applies to the whole
state region, and you get a notification.

### Enabling homeland changes

Nothing changes until your country enables homeland changes with one of these:

- the Ancestral Citizenship law (Citizenship), Violent Hostility (Minority
Rights) or Linguistic Purity (Language Policy);
- tier II or higher of the Cultural Unity principle in your power bloc;
- the Mass Media technology.

You must also own the whole state region. Losing either condition pauses every
project in the state, and the Homeland Dynamics tile says why. Progress resumes
where it stopped.

### Homeland thresholds

A primary culture without a homeland in the state can start forming one once it
makes up at least the creation threshold of the state's population, 60% by
default. Laws and principles move the creation threshold, but never below 10% or
above 90%.

A culture with a homeland in the state that is not one of your primary cultures
starts losing it once its share falls below the removal threshold. The default
removal threshold is 0%, so no homeland can be removed until a law or principle
raises it.

A culture's progress resets to zero if the state changes owner or the culture
stops qualifying; the tile marks such a project before it is cleared.

### Speed of homeland change

A project gains 10 percentage points a year by default, so a homeland forms or
disappears in ten years. The Homeland Change Speed modifier scales that rate.
Turmoil of 25% or more multiplies it by 1.25, and 50% or more by 1.5. Legitimacy
below 25 halves it, and legitimacy of 75 or more multiplies it by 1.25. The rate
stays between 1 and 95 points a year. The Promote National Values decree adds
+300% speed in its state, which on its own brings a change down to 30 months.

Laws and principles that move the three numbers:

| Law or source | Creation threshold | Removal threshold | Change speed |
|---|---|---|---|
| Ancestral Citizenship | −20% | +10% | +50% |
| Violent Hostility | −20% | +10% | +25% |
| Ghettoization | −15% | none | none |
| Linguistic Purity | −10% | +10% | +50% |
| Cultural Assimilation | −10% | +5% | +25% |
| Racialized Citizenship | −10% | +5% | +25% |
| Protection | +10% | −5% | −15% |
| Affirmative Action | +20% | −10% | −25% |
| Universal Citizenship | +20% | −5% | −25% |
| Cultural Unity principle, tier II / III / IV / V | −5 / −15 / −25 / −35% | +5 / +10 / +20 / +40% | +5 / +10 / +20 / +30% |

Other Citizenship, Minority Rights and Language Policy laws, a few technologies
and the language-reform amendments move them too; the tile's tooltip lists every
source. Under Ancestral Citizenship alone, a primary culture needs 40% of a
state to start a homeland, a minority's homeland goes once it falls below 10%,
and each change takes under seven years.

## Cultural acceptance and minorities

When a new cultural community appears in a state, the base game gives it a
temporary local acceptance penalty that wears off over time. The mod adds two
state modifiers that act on that penalty:

- Annual Cultural Acceptance closes the penalty faster, adding its value in
acceptance over a year to every culture that still carries one. The Cultural
Integration decree gives +5, the Ministry of Refugee Affairs +0.2 per level, and
tiers III to V of the Cultural Plurality principle +0.25 to +0.5.
- Minimum Local Acceptance limits how deep the penalty can go: no deeper than
−40 plus the modifier's value. Indifference gives +5, Protection +10 and
Affirmative Action +20 (all Minority Rights laws), and Cultural Plurality tiers
III to V give +5 to +10. Without either modifier there is no floor.

These matter most where migration keeps bringing new communities into a state.

The Violent Hostility law and the Cultural Emigration Initiative decree give a
state Violence Against Minorities. Each year, every culture there with
acceptance below 60 risks an outbreak, more likely the lower its acceptance. A
severe outbreak kills 10% of that culture in the state, radicalizes the
survivors, devastates the region and sets off a mass migration; a lesser one
kills 2% and does the same on a smaller scale. Minority laws are in [Rights and
society laws](05-politics.md#rights-and-society-laws).

## State tourism

Tourism is a luxury good in the mod, made by the Tourism Industry building
(unlocked by Romanticism, see [The extended timeline](02-timeline.md)) and
bought by wealthy pops. Two state modifiers, refreshed monthly and shown on the
tourism card, set how much a Tourism Industry makes: Tourism Output and Tourism
Throughput.

### Tourism output

Two sources on the card set a state's output bonus:

| Source | Bonus |
|---|---|
| Base Appeal | A fixed score for each state region, from its scenery, climate and history. It runs up to +100%; Wyoming scores 90%, Nebraska 20%, and any region without its own score gets 20%. Nothing changes it. |
| Cities | +100% for the largest city in the world, 5% less for each place below it, nothing below 20th. See [World city rankings](#world-city-rankings). |

The card's "All modifiers" line adds everything else that changes output. An
Airport or Spaceport adds +15% per level, scaled by staffing. Laws add between
−30% (Secret Police, Outlawed Dissent) and +15% (Universal Citizenship).
Pollution, turmoil and obstinance cut output in proportion to how bad they are,
at their worst by 200%, 100% and 50%, so heavy pollution can shut a state's
tourism off entirely.

### Tourism throughput

Five sources set a state's throughput bonus, each with a bar toward its cap:

| Source | Bonus | Cap |
|---|---|---|
| Ports | +0.2% per Port level up to 100, then +0.04% per level up to 500 | +36% |
| Transit | +0.1% per Railway level and per Highway level up to 100, then +0.02% per level up to 500 | +18% from each |
| Art | +1% per Creative Industries level up to 20, +0.25% up to 100, +0.05% up to 500, +0.01% up to 1,500 | +70% |
| Parks | +25% with a National Park | +25% |
| Monuments | +10% for a Skyscraper, +25% for each monument | none |

The "All modifiers" line for throughput also carries the Promote Tourism decree
(+50%), a Grand Monument (+1% per level) and bonuses from events.

## World city rankings

Each month the game ranks every state in the world by city size: the services it
produces (only with an Urban Center), weighted up by its average standard of
living, ×1.5 for a capital and ×1.5 for a great power's states, halved for an
unrecognized country. The tourism card shows the rank. The top 20 get the Cities
bonus to tourism output, from +100% for first to +5% for twentieth; nothing else
uses the ranking.

## Internal resettlement

Internal resettlement is government-run settlement of an empty frontier. You
build a Settlement Authority in a thinly populated state. Each month it recruits
settlers across your country under its program and moves them there. You never
choose a culture or religion to move: programs select by occupation, strata,
acceptance and radicalism.

The Internal Resettlement game rule has three settings. Enabled (the default)
gives everyone every program their laws allow. AI Voluntary Only is the same for
players, but each month it switches AI countries off Penal Transportation,
Special Settlements and Rustication. Disabled removes the system. Moving people
between countries by treaty is a different mechanic, the Population Transfer
article in [Diplomacy](08-diplomacy.md).

<!-- screenshot: a Settlement Authority's building panel with its program, settlement plan and transport methods, and the Settlers arrived last month readout -->

### The Settlement Authority

The Settlement Authority is a government building available from the start of
the game, with a low construction cost. It can only be built on an open
frontier, measured over the whole state region whoever owns each part:

- a new Authority needs fewer than 2 people per km²;
- an existing one keeps running, and can add levels, until the region reaches
10 people per km².

Both densities scale with Migration Crowding Tolerance, and the building's
requirements show the region's current density against them. In an 1836 start
the open frontiers include the American West, Siberia, the Kazakh steppe,
Hokkaido and the Argentine pampas.

An Authority can have up to 5 levels. Nationalism, Civilizing Mission, Mass
Propaganda, Keynesian Economics and Civil Rights Movement each add 5, to a
maximum of 30. Capacity and costs scale with level.

When the region reaches the closing density, the Authority is wound up and you
get the event "The Frontier Is Closed". To keep settling, build one on the next
frontier.

### Resettlement programs

The Resettlement Program method decides who is recruited and how many move each
month. Half the capacity comes with each level and half depends on staffing, so
a new Authority moves settlers from the first month and speeds up as it fills
its jobs. The state's modifiers show the total as Settlers Moved per Month.

| Program | Needs | Recruits | Moved per month per staffed level | Die in transit |
|---|---|---|---|---|
| Land Grants | nothing | Unemployed and peasants of the lower strata who are at least second-class citizens; no peasants under Serfdom | 300 | none |
| Military Colonies | Standing Army | As Land Grants, but fully accepted only | 250 | none |
| Penal Transportation | Law Enforcement; not under Guaranteed Liberties | Lower-strata pops in which at least a fifth are radicals | 100 | 5% |
| Organized Colonization | Railways | Unemployed, peasants and laborers of the lower strata who are at least second-class citizens | 500 | none |
| Special Settlements | Mass Propaganda and Collectivized Agriculture; not under Guaranteed Liberties, Protected Speech or Right of Assembly | Farmers | 1,000 | 15% |
| Development Program | Keynesian Economics | As Organized Colonization, plus machinists, engineers and clerks, all at least second-class citizens | 800 | none |
| Rustication | Mass Media and Single-Party State | Laborers and clerks who do not work in farming, plantations, ranching or subsistence | 800 | 1% |
| Managed Retreat | Environmental Movement | Everyone except slaves, from coastal states while you suffer Coastal Flooding or Coastal Population Relocation, and from states hit by a nuclear strike or a weapons accident | 600 | none |

Programs cost bureaucracy, paper and staff. The voluntary programs and Managed
Retreat also use services; Military Colonies and the coercive programs (Penal
Transportation, Special Settlements and Rustication) hire soldiers and use small
arms instead. Slaves are never recruited. If a law change retires the running
program, the Authority falls back to Land Grants. Managed Retreat's damage comes
from [Climate events](14-climate.md#climate-events) and [What a nuclear strike
does](13-nuclear.md#what-a-nuclear-strike-does).

Each program also speeds up the destination's incorporation and its growth as a
colony, by 10% to 25%. Military Colonies also reduce the effect of turmoil there
by 25%, and Penal Transportation and Special Settlements raise mortality there.
These bonuses grow with the month's arrivals and reach full strength at 2,000
settlers a month, so a small or idle Authority buys little of them.

### Settlement plans and transport

The Settlement Plan decides what settlers build. Any plan works with any
program, and every plan adds +1 migration pull per level to help the frontier
hold its settlers.

| Settlement plan | Needs | Effect on the destination |
|---|---|---|
| Homesteads | nothing | Virgin Soil: +10% farm and ranch throughput and more subsistence output. No arable land is added, and the bonus ends with the Authority. |
| Work Settlements | nothing | The Authority employs 100 laborers per level and uses tools; +10% mining and logging throughput, more infrastructure. |
| Planned Towns | Modern Urban Planning | +10% construction, more infrastructure and migration pull; employs engineers and uses services. |

The settlement bonuses scale with arrivals in the same way as the program's.

Transport adds capacity and costs transportation goods:

| Transport | Needs | Extra settlers per month per level |
|---|---|---|
| Overland | nothing | none |
| Rail and Steamship | Railways | +200 |
| Motor Transport | Combustion Engine | +400 |
| Airlift | Commercial Aviation | +600 |

### How settlers are recruited

Each month an Authority works down your other states, most eligible people
first, until its capacity is met; it skips other Authorities' states. A state
gives at most 2% of its eligible people a month across all your Authorities, and
any draw of fewer than 100 people from a pop is skipped, so a pop smaller than
5,000 is never recruited. The Authority shows "Settlers arrived last month" and
"Died in transit last month", and each source state shows how many it gave.

The Resettlement Recruitment Drive decree steers recruitment. Every Authority
recruits from a drive state before any other, and may take 4% of its eligible
people a month instead of 2%, which reaches pops of 2,500 or more. The decree
lowers the state's migration pull by 10% and needs at least one Authority
elsewhere.

### Costs and consequences of resettlement

Coercive programs lose some recruits in transit. Special Settlements radicalize
the farmers left behind, and Rustication the laborers and clerks.

Settlers press on the people already there: each month, destination pops below
second-class citizens gain radicals in proportion to the arrivals.

Each program has one political modifier for your country, however many
Authorities run it. It reaches full strength when the program settles 0.25% of
your population a year, and fades over several years after it stops (a third is
left after one year).

| Program | Interest group approval at full strength |
|---|---|
| Land Grants | Rural Folk +3, Landowners −3 |
| Military Colonies | Armed Forces +3, Rural Folk −3 |
| Penal Transportation | Intelligentsia −3 |
| Organized Colonization | Rural Folk +3 |
| Special Settlements | Rural Folk −10, Intelligentsia −5 |
| Rustication | Intelligentsia −10, Petite Bourgeoisie −5 |
| Development Program, Managed Retreat | none |

If you are a party to the Universal Declaration of Human Rights, a UN convention
([UN conventions and
agencies](09-united-nations.md#un-conventions-and-agencies)), running Penal
Transportation, Special Settlements or Rustication gives you Violating the
Declaration: up to −10% prestige as the programs grow, halved if you ratified
with reservations. It fades over several years after they stop. The first month
you run a coercive program as a party, an event explains the penalty and offers
to switch every coercive program to your best voluntary one.

Settlers change the culture shares at the destination. Over time that can create
or remove a homeland there, under the rules in [Dynamic
homelands](#dynamic-homelands).

### Resettlement events

You draw at most one resettlement event every eighteen months, however many
Authorities you run, set in an Authority that received settlers that month.

| Event | Fires for | Choices |
|---|---|---|
| Land Rush | Voluntary programs | +2,000 settlers a month for a year and more land pressure, or +10% construction there for two years. |
| The Speculators | Voluntary programs | −50 authority for two years (Rural Folk approve), or 500 fewer settlers a month for two years (Landowners and Industrialists approve). |
| A Hard Winter on the Frontier | Any program | Money, or deaths, radicals and lower migration pull there for a year. |
| Dust Storms | Homesteads after ten years | Money and a small farm penalty for ten years, or a decaying −20% farm and ranch penalty. |
| The Reform Campaign | Coercive programs | End them for prestige, or defy the critics for a prestige penalty. |
| Famine in the Settlements | Special Settlements | Money, or deaths and radical farmers. |
| A Petition to Return | Coercive programs after five years | Switch that Authority to a voluntary program and let one in twenty of its lower-strata citizens go home, or face radicals. |
| Land Disputes | Destinations with inhabitants below second-class citizens | Money, authority and 300 fewer settlers a month for ten years to calm them, or back the settlers and radicalize them. |

### Resettlement and the AI

The AI values a Settlement Authority on an open frontier when one of its states
has unemployment above 5% or migration crowding, and on any frontier emptier
than 0.5 people per km². It stops founding new ones once it has three. It issues
the Recruitment Drive in states with unemployment above 10% or a crowding
penalty above 10%. The mod gives the coercive programs a low AI weight, but only
the AI Voluntary Only rule guarantees that AI countries stay off them.
