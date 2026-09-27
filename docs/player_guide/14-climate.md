# Climate and pollution

Burning coal and oil warms the world in this mod. Every market's emissions add
to one global total, the total sets a global temperature anomaly, and the
anomaly drives penalties that every country shares. The Global Warming journal
entry tracks it and holds the climate policies you can adopt. The Global Warming
game rule (on by default) controls all of this; with it off, the world never
warms. State pollution, the Environmental Movement and the pollution scandal
event work under either setting.

## How emissions become warming

Emissions belong to a market, not a country. Each year a market emits in
proportion to the coal and oil consumed anywhere in it, cut by the emission
reductions of its market leader and reduced by the carbon captured by Synthetic
Fuel Works and Carbon Conversion Works in the market. The year's emissions of
every market are added to the world's cumulative total, and the temperature
anomaly is that total divided by 10,000: a market that emits 1,000 a year warms
the world by 0.1 °C a year.

Warming does not wear off. The anomaly falls only in a year when the world as a
whole captures more carbon than it emits. Cutting your emissions slows the rise;
it does not undo what is already there.

Only the market leader's reductions count, and they apply to the whole market.
The leader's Greenhouse Gas Emissions modifier comes mainly from the three
market-wide climate policies, the Ministry of the Environment (−5% per level)
and the Environmental Sustainability power bloc principle (−5% to −25% by tier).
A member's own ministry does nothing for the market's emissions.

## The Global Warming journal entry

The entry is listed, greyed out, for every country from the start of the game.
It activates for everyone once the anomaly reaches 0.1 °C and then stays
active: it never completes and never goes away, even if the world cools again.
Its progress bar fills at 4 °C, but the penalties keep growing past that.

| Anomaly | Status |
|---|---|
| Below 0.1 °C | Negligible |
| 0.1–0.5 °C | Slight |
| 0.5–1.0 °C | Moderate |
| 1.0–2.0 °C | Significant |
| 2.0–3.0 °C | Severe |
| 3.0 °C and above | Catastrophic |

### The Climate Warming modifier

Each month the entry gives every country the Climate Warming modifier, with
every value multiplied by the current anomaly. At 1 °C it is:

- +5% mortality and −1 standard of living in every state;
- −10% farm throughput and −2.5% throughput for every building;
- +5% construction goods used by buildings;
- +1% migration quota, as climate refugees move;
- 25% worse floods, droughts, extreme winds and torrential rains, and 50% worse
  heatwaves and wildfires, in both impact and duration;
- 15% milder frost and hailstorms, and weaker pollinator surges and moderate
  rainfall.

At 2 °C every line doubles, and at 3 °C it triples. The dashboard's Warming
Penalty Scale shows the current multiplier.

## The climate dashboard

The journal entry holds three panels.

<!-- screenshot: the Global Warming journal entry with the Climate Conditions and Mitigation Policies panels open -->

Climate Conditions shows the Global Temperature with its status, the Change Last
Year, Our Market's Emissions (with the amount captured), our Share of World
Emissions, the Emissions Cut In Force (the percentage and how many of the eight
policies are active), Our Role in the market, and the Warming Penalty Scale.
Each row's tooltip explains the reading. The emissions and yearly figures are
recalculated each January; the cut and the policy count change the moment you
adopt or repeal.

Mitigation Policies lists all eight policies for every country, each with an
Adopt or Repeal control and a status: Active, Inactive, or set by market leader.
A greyed control's tooltip lists the conditions and which of them you meet.
Adoption Around the World, a collapsible section, counts the nations running
each policy.

History, collapsed by default, charts global temperature and your market's
share of world emissions, one point a year.

## Climate policies

There are eight policies. Three are market-wide: only a market leader can adopt
or repeal them, and they then apply to every country in its market, which sees
them as "set by market leader". The other five are national, open to every
country. Every policy needs the anomaly to have reached 0.5 °C, except
Fossil-Fuel Divestment, which needs 1.0 °C.

Most policies carry an Authority Cost for as long as they are in force, and you
can only adopt one while you produce more authority than that cost.

| Policy | Scope | Authority | Effects |
|---|---|---|---|
| Carbon Tax | Market | none | Emissions −20%; coal and oil output −10%; taxes on coal mining and oil extraction doubled, manufacturing taxes +10%. |
| Renewable Investment | Market | none | Emissions −15%; Renewable Energy Plants +10% throughput but need subsidies; conventional power plants −10% throughput; power buildings built 25% faster. |
| Emission Standards | Market | 200 | Emissions −10%; generated pollution −25%; −5% throughput for every building. |
| Climate Adaptation | National | 250 | Mortality −2.5% and standard of living +0.5 in every state. |
| Reforestation Subsidies | National | 100 | Farm throughput +5%; droughts and floods 25% weaker and shorter. |
| Public Transit | National | 150 | Transportation output +10%; oil input −5%; infrastructure built 10% faster; pops' automobiles give 0.25 less infrastructure per unit. |
| Fossil-Fuel Divestment | National | 200 | Taxes on coal mining and oil extraction +25%; coal and oil input −5%. |
| Green Building Codes | National | 100 | Construction goods input +5%; electricity input −2.5%. |

Only the three market-wide policies cut the emissions figure directly. The
national ones trim oil, coal and electricity use at the margin, protect your
people from the damage, and calm the Environmental Movement
([The Environmental Movement](#the-environmental-movement)). Climate Adaptation
is the one that pays off even if nobody else acts, and it is worth most to poor
countries.

If you lead a market that burns a large share of the world's coal and oil, the
market-wide policies are where your choice matters. If you are a member, you can
only protect yourself: the leader decides your market's emissions.

## How the AI adopts climate policy

Each AI country weighs each policy separately, from its own conditions, and
keeps the ones those conditions support. Every policy's will starts from a
shared core: 20 points per degree of warming (at most 100), 15 more with the
Ministry of the Environment established, and 8 more if an environmentalist
leads an interest group in government. Five signals then push it up or down,
weighted by who each policy costs or helps:

- laissez-faire economics, against every policy;
- industrialists in government, against the policies that burden industry;
- the Environmental Movement's support, for every policy;
- standard of living against the world average: wealth favors most policies
  but counts against Climate Adaptation and Reforestation Subsidies;
- how far the market is a net exporter of coal and oil, strongly against the
  Carbon Tax and Fossil-Fuel Divestment.

The AI adopts a policy once its will reaches the policy's threshold and it has
the authority, and repeals only once the will falls 15 points below the
threshold, or while its authority is negative. Between the two it leaves the
policy alone, so an election doesn't flip policies back and forth.

| Policy | Threshold |
|---|---|
| Climate Adaptation | 25 |
| Reforestation Subsidies | 30 |
| Renewable Investment | 35 |
| Public Transit | 40 |
| Green Building Codes, Emission Standards | 45 |
| Carbon Tax | 55 |
| Fossil-Fuel Divestment | 70 |

In practice most countries take up Climate Adaptation around 1.25 °C if they
have the authority, countries with an environment ministry move early, and
Fossil-Fuel Divestment is rare below 3 °C. A laissez-faire oil exporter may
never divest.

## Enforce Emissions Reduction

Enforce Emissions Reduction is a treaty article that forces a market leader to
run every climate policy except Climate Adaptation. It appears once the world
has warmed past 0.1 °C and can be signed from 0.5 °C, with the Intergovernmental
Organizations technology, against a country that leads its own market. It can
be a war goal, and it can be requested or offered in a treaty.

On entry into force, the bound country adopts the three market-wide policies
for its whole market and the four national emissions policies for itself. While
the treaty holds, it can't repeal them, and it also suffers −20% power plant
throughput, −10% coal mining and oil extraction throughput and +300 Authority
Cost. The demanding side gains +2% prestige and pays the article's upkeep. If
the bound country loses one of the policies anyway, the treaty freezes. Treaty
mechanics are in [Diplomacy](08-diplomacy.md); while a United Nations exists, it
also negotiates climate accords ([The United Nations](09-united-nations.md)).

## Climate events

Two kinds of event come with warming. The threshold events fire once for every
country as the world crosses each mark, and the recovery events fire once if it
falls back below a mark it had passed:

| Event | When |
|---|---|
| The Mercury Rises | Warming reaches 0.5 °C |
| The Sweltering Season | 1.0 °C |
| When the Levees Break | 2.0 °C |
| The Reckoning | 3.0 °C |
| Off the Brink, The Heat Recedes, A Cooler Decade, Below the Line | Warming falls back below 3.0, 2.0, 1.0 and 0.5 °C |
| Near Baseline | Warming falls back below 0.1 °C |

Each month every country also has a small chance of one recurring event whose
conditions it meets. Their choices trade money, authority and interest group
approval against radicals, mortality and throughput, and three have an extra
option for a country that funds its Ministry of the Environment to level 3.

| Event | Conditions |
|---|---|
| These Dark Satanic Chimneys (a pollution scandal) | Coal Mines or Oil Rigs of level 3 or more; fires even with the rule off |
| A Greener Shade of Politics | 0.5 °C and Pollution Control |
| The Uprooted (climate refugees) | 1.0 °C |
| The Tide Comes In (coastal flooding) | 1.0 °C and a coastal state with a Port |
| The Congress of Smoke (a climate summit) | 1.0 °C, a major power with Pollution Control, and no United Nations |
| The Barren Harvest | 2.0 °C and Wheat Farms |
| The Wells Run Dry, The Fever's March | 2.0 °C |
| The Great Thaw | 2.5 °C and a coast |
| Green and Gold | 3.0 °C, Clean Energy Technologies and industrialists in government |
| Quiet Power | Environmental Movement and a Renewable Energy Plant |
| Friends in High Places | A Carbon Tax, Emission Standards or Fossil-Fuel Divestment, and Coal Mines or Oil Rigs of level 5 or more |

The Tide Comes In can leave you with Coastal Flooding or Coastal Population
Relocation; while either lasts, a Settlement Authority on Managed Retreat can
move people off your coasts ([States and population](07-states.md)).

## State pollution

The mod adds a Generated Pollution modifier that scales how much pollution a
state's buildings produce, recalculated monthly. It is lowered by:

| Source | Generated Pollution |
|---|---|
| Pollution Control decree (needs Pollution Control) | −50% |
| Emission Standards policy | −25% |
| Ministry of the Environment | −5% per level |
| Electric Vehicles | −5% |

Each level of the Ministry of the Environment also cuts emissions by 5% and
raises the National Park level cap by one, at a small cost to mining, logging
and oil extraction throughput and to construction goods.

Heavy pollution hurts more than in the base game. As a state region's pollution
rises toward its maximum, it adds up to +5% mortality, −3 standard of living and
−5% working-age population on top of the base-game penalty, and wipes out
tourism output. It also damps new pollution by up to 90%, so a region that is
already choked fills up more slowly.

### The Environmental Movement

The Environmental Movement is a political movement that forms once you research
Pollution Control, if you have not established the Ministry of the Environment.
Its support comes from polluted states, from academics and literate middle-class
pops, and from warming, rising at 0.5, 1.0, 1.5 and 2 °C; the Environmental
Movement technology doubles it. Each climate policy you have in force lowers its
radicalism, each one you could adopt but haven't raises it, and so does each
unfunded level of the ministry. It disbands once the Ministry of the Environment
is established and funded to its maximum. Its support also pushes AI countries
toward climate policies.
