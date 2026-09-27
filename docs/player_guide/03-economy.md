# Economy and construction

This chapter covers how the mod changes the way your economy builds, consumes
and stores. The largest change is the construction market: construction is a
good that Construction Sectors sell and that your government and investors buy,
and most industry uses a little of it as upkeep. It runs from the first day of
the game under the Free Market Construction game rule, which also offers three
reduced settings. The rest of the chapter covers what construction costs in rich
countries, how living-standard expectations adapt, what wealthy pops buy, the
Bulk Transportation good, the Strategic Reserve journal entry, wartime demand
for ammunition and the mod's new mineral deposits.

## The construction market

In the base game, each Construction Sector adds construction points straight to
a national pool. Under Free Market Construction, the default setting of the game
rule of the same name, construction is a tradeable good instead. Construction
Sectors sell it on the market like any factory, your government and your
investors buy it every week, and what they buy becomes the points your two
construction queues spend. The system is based on TOGFan's Free Market
Construction mod.

### From Construction Sector to construction queue

Each week, construction moves through four steps.

1. Construction Sectors produce the good, which your market lists as
   Construction Services (base price £1,000). In a market game the sector is
   ordinary heavy industry: investors build it when it pays, and your government
   can build it too. Barracks under the Engineering and Logistics power bloc
   principle add a little.
2. The government buys the number of points you set in the construction panel,
   paid from the treasury.
3. Investors buy for private projects on their own, paid from the investment
   pool. They spend roughly the pool's weekly income, more when the pool has
   built up and less when it runs low.
4. Construction Sites turn the purchased good into construction points. They
   appear on their own in every state where construction is under way, and in
   your capital when nothing is under way anywhere else. Nobody builds them.

Each purchase is capped at what its queue can use that week: at most one week's
maximum progress for each level in the queue. The share of points that goes to
private projects is recalculated every week from the two purchases, and your
economic-system law no longer sets it.

When all buyers together want more construction than is on sale, the price
rises: construction costs the treasury more, and investors' money buys fewer
points. Construction then slows, however much money the treasury or the
investment pool holds. Every country in your market buys from the same supply,
and construction is imported and exported like other goods.

Each level of a Construction Sector produces more with better production
methods:

| Production method | Construction per level each week |
|---|---|
| Wooden Buildings | 1 |
| Iron-Frame Buildings | 2 |
| Steel-Frame Buildings | 3.5 |
| Arc-Welded Buildings | 5 |
| Reinforced Concrete Buildings | 6 |
| Advanced Construction | 10 |
| Nanomaterial Buildings | 16 |

### Construction maintenance and retooling

Most factories, power plants, railways, ports, airports, highways, trade centers
and skyscrapers use 0.1 construction per level each week as maintenance. Farms,
ordinary mines, plantations and urban centers don't. A few company buildings
also use construction in their production. This upkeep competes with your
queues for the same supply, so a growing economy needs a growing construction
sector.

When a building switches production method it gets the Production Method
Retooling modifier, which raises its construction use by +1,000% right after the
switch, falling steadily to nothing over five years (260 weeks); the building
shows when the modifier expires. Just after switching methods, a 20-level
factory goes from 2 construction a week to 22, before cost scaling.

### Reading the construction panel

The Construction Market section sits at the top of the construction panel's
domestic tab.

<!-- screenshot: the Construction Market section of the construction panel, with the purchase control and the four read-out lines -->

| Line | What it shows |
|---|---|
| Purchase control | The government purchase you have set. Click for ±1, Shift+Click ±10, Ctrl+Click ±100, Alt+Click ±1,000. Right-click on the plus adds 10,000; right-click on the minus sets 0. |
| Government buys | Points bought this week and the approximate treasury cost. "Capped at what the queue can use" appears when your setting is higher than the queue can take. |
| Private investors buy | Points investors bought this week and the share of construction going to private projects. |
| Price | What one construction point costs now: the market price, raised in rich countries by Construction Cost Scaling. |
| Your market | Construction on sale (including imports) against construction wanted (every buyer, including maintenance and exports). A red "shortage" marks demand above supply. |

### Free Market Construction settings

The game rule has four settings, fixed when you start the campaign.

| Setting | Construction good | Maintenance | Retooling | Private share of construction |
|---|---|---|---|---|
| Enabled (default) | Traded on the market | 0.1 per level | +1,000%, fading over five years | Follows the two purchases |
| Without Retooling Costs | Traded on the market | 0.1 per level | None | Follows the two purchases |
| Without Maintenance | Traded on the market; a few company buildings still use it in production | None | None | Follows the two purchases |
| Disabled | None | None | None | Set by your economic-system law |

With the rule disabled, construction works as in the base game, but the
Construction Site takes the Construction Sector's place. The government builds,
expands and downsizes Construction Sites like any government building, and each
level provides 1 to 16 points a week by production method, the same tiers as the
table above. The government pays their wages, and they buy materials for each
point your queues spend. For now, Construction Sites have to be built from the
state view. Every country also gets Base Construction, 5 points a week, so a
country without any sites can still build its first one. The construction panel
shows a Direct Construction section with your construction per week and the
private share, which the economic-system law sets: 25% under Traditionalism, 50%
under Interventionism, Agrarianism, Extraction Economy and Industry Banned, 75%
under Laissez-Faire, 35% under Cooperative Ownership and 10% under Command
Economy.

### Running the construction market

- Your government purchase starts at 0 in a new game. Set it in your first week,
  or the government queue builds nothing.
- A high purchase setting is harmless, because only what the queue can use is
  bought. To stop government construction while private building carries on, set
  it to 0; the sector keeps selling to investors.
- Watch the market line. A standing shortage means you need more Construction
  Sector levels or a better production method. Cheap wood, iron and steel make
  construction cheaper, because the sector buys them.
- A high price makes Construction Sectors profitable, and investors then build
  them on their own.
- Spread production-method switches out. Every switch adds five years of
  retooling upkeep, heaviest in the first months, and switching a whole
  industry at once can take the construction your queues were counting on.
- Don't downsize the last Construction Site. A new one appears in your capital
  the next week, but construction stops for about two weeks.

AI countries choose their own purchase each week. They spend roughly their net
income, more when their gold reserves are full and less when they carry debt.
They cut back when a war or banking stress meets thin reserves, and buy at least
10 points a week while their government queue has anything in it.

## Construction costs in rich countries

Two mechanics make construction dearer as a country grows rich, and both work in
every setting of the Free Market Construction rule.

### Construction Cost Scaling

Once a year, the game compares your GDP per capita with a fixed curve. Above £1
per person per year, the Development Cost Scaling modifier raises the
construction each point requires. The increase rises in a straight line to
+1,000% at a GDP per capita of £100, about 10 percentage points for every £1. It
applies to every use of construction: the points your queues spend and the
maintenance your buildings pay. It combines by multiplication with other
construction-cost modifiers, so another modifier that cuts construction costs by
20% still cuts 20% in a rich country. With Free Market Construction disabled,
the same scaling raises the cost of the materials your construction uses instead.

This is a catch-up mechanic: a rich country needs more construction for each
building and each level of upkeep, while a poor country builds cheaply.

### Excess private construction

Once a year, the game also checks whether investors have more than 500 levels
waiting in the private queue while the investment pool is still growing. If so,
you get Excess Private Construction. Each project can then absorb more
construction a week, so the pool can spend its money, at a small cost in
construction efficiency that grows with the modifier; the tooltip lists the two
effects as Max Weekly Construction Progress and State Construction Efficiency.
The modifier moves by at most about a fifth a year. If it grows very large while
the investment pool holds more than your yearly GDP, Overinvestment follows for
a year and pops stop paying into the pool.

## Adaptive standard-of-living expectations

In the base game, pops expect a standard of living set by their stratum,
literacy and laws, and pops below that expectation turn radical over time. The
mod drops the literacy part and adds Adaptive SoL Expectations: an extra
expectation that follows your country's actual average SoL, with a delay. It
aims at a level 10 SoL below your average SoL, moved up or down by some
technologies and laws, and each month it closes part of the gap:
about half of it in ten years and three-quarters in twenty. It only ever adds
to the base-game expectation. While your SoL is too low for that level to reach
the base-game expectation, expectations stay at the base-game level.

So the direction of your economy matters as much as its level. After a sudden
rise in SoL, expectations lag behind for years, pops live better than they
expect, and fewer turn radical. After a sudden fall, expectations stay high for
years and pops sit below them, which feeds radicals long after the shock itself.
Slow, steady growth is the calmest path. You see the adjustment as three country
modifiers: Lower, Middle and Upper Class Expectations Shift.

Technologies, laws and literacy move expectations further:

- The society technologies Egalitarianism, Labor Movement, Socialism, Political
  Agitation and Mass Propaganda each raise the level expectations settle at by
  0.5 SoL. They replace the literacy-based increase those technologies give in
  the base game. Several of the mod's later technologies and laws raise or lower
  it too, and Industry Banned lowers it by 1.
- Voting laws raise the expectations of the classes that hold power under them:
  Autocracy, Landed Voting and Wealth Voting raise the upper class, Universal
  Suffrage the lower class. Regulatory Bodies and Workers' Protections raise the
  lower class.
- Poor Laws, Wage Subsidies and Old Age Pension keep expectations at least 1, 2
  or 3 SoL above the base-game level, however long hard times last. Universal
  Basic Income raises that floor to 10 SoL and the Post-Scarcity Economy to 15.
- Literate populations compare themselves with the world. When the world's
  average SoL is above yours, their expectations rise; when it is below, they
  fall.

## Pop consumption at high wealth

Pops in the base game stop at wealth 99; in the mod they can reach wealth 200.
Three new needs appear as pops grow rich:

| Need | Starts at wealth | Goods that meet it |
|---|---|---|
| Convenience | 20 | Services, Consumer Appliances, Digital Access, Software |
| Art | 25 | Art and Entertainment, some Services |
| Tourism | 25 | Tourism, some Personal Transportation |

These needs, and Services, grow steeply with wealth: at wealth 60, Services and
Convenience make up more than half of what a pop buys. Tourism as an industry is
covered in [State tourism](07-states.md#state-tourism), and the new goods in
[The extended timeline](02-timeline.md), which also lists the base-game goods
the mod renames. In the table above, Personal Transportation is the base game's
Transportation and Art and Entertainment its Fine Art. Chemicals, in the
Strategic Reserve below, is its Fertilizer.

## Bulk Transportation and freight

The base game's Merchant Marine good is renamed Bulk Transportation, and it now
stands for freight of every kind, by rail, road, sea and air.

It is produced by transport infrastructure:

- Ports, as in the base game, and their later methods: Container Ports, Global
  Ports and Magnetic Drive Ports.
- Railways, on their train methods and on their Centralized Traffic Control,
  Containerized Cargo and automated loading methods.
- Highways, on every method.
- Airports, including their Spaceport method.
- Company buildings such as trading houses, logistics hubs, docks, shipyards
  and canal companies.

It is consumed across the industrial economy:

- Trade Centers, as in the base game.
- Construction Sectors from Iron-Frame Buildings onward.
- The rail-transport and tanker-car methods of logging camps, mines,
  plantations and oil rigs, and the refrigerated rail car and flash-freezing
  methods of fishing wharves, whaling stations and ranches.
- Later mining methods, such as dragline excavators and geophysical surveys, and
  the deeper oil-well methods.
- Many late-game factory and retail methods, from advanced assembly lines and
  AI-managed production to e-commerce, department stores and shopping malls.

An agrarian economy barely touches it. An industrial one needs railways, ports
and highways to keep up, and a Bulk Transportation shortage raises costs across
construction, mining and industry at once.

## The Strategic Reserve

The Strategic Reserve journal entry lets you stockpile strategic goods in your
capital, buying them when they are cheap and releasing them when prices rise or
supply fails. It is shown once you research Logistics and becomes active when
you build a Strategic Reserve Hub. No game rule controls it.

### Reserve hub and silos

Two buildings make up the reserve, both unlocked by Logistics.

| Building | Where | Construction cost | Each level adds | Staff per level |
|---|---|---|---|---|
| Strategic Reserve Hub | Capital only, one per country | Low | 5,000 storage for each good; each good may move 1,000 units a week | 5,000 |
| Strategic Reserve Silo | Any state | High | 1,000 storage for each good; +100 to each good's weekly limit | 500 |

The hub is the reserve: it holds the controls and does the buying and selling.
It can't be downsized or demolished. Silos only add room and flow, and do
nothing without a hub. The hub trades only when it is fully staffed. Below full
occupancy the journal entry shows the hub as deactivated, and it neither trades
nor replaces what decays.

### Reserve goods and decay

The reserve holds eight goods. Stock decays every week at a yearly rate that
technology lowers.

| Good | Available from | Decay per year at first | After all technologies |
|---|---|---|---|
| Grain | Always | 25% | 0% |
| Small Arms | Always | 1.5% | 0.7% |
| Artillery | Always | 1% | 0.4% |
| Ammunition | Percussion Cap | 2% | 0.5% |
| Oil | Fractional Distillation | 0.5% | 0.05% |
| Chemicals | Intensive Agriculture | 4% | 0.1% |
| Aeroplanes | Military Aviation | 4% | 2% |
| Tanks | Mobile Armor | 2.5% | 1.4% |

Aeroplane and tank decay rises for a time with jets, stealth aircraft and
composite armor before later technologies bring it down. The hub buys each
week's decay on top of whatever rate you set, so a rate of 0 holds a stockpile
steady at a small ongoing cost. The good's row tooltip breaks its decay rate
down by source.

### Storing and releasing reserve goods

Each good has a row in the journal entry with a fill bar, a status (Storing,
Withdrawing, Idle or Blocked) and decrease, stop and increase buttons. Click the
good's name to expand the row: stock against capacity, your rate setting, what
actually moved last week, decay, and the good's policy.

<!-- screenshot: the Strategic Reserve journal entry with one good's row expanded and its policy settings open -->

A positive rate buys that many units a week from the market into the reserve; a
negative rate releases that many onto the market. Every button press moves the
rate by the shared adjustment step, which the Cycle Step Size button sets to 1,
10, 100, 1,000 or 10,000 (10 at first). Reset Reserve Rates sets every rate to
0. The game keeps each rate within the weekly flow limit and the room or stock
left, and sets it to 0 when the reserve fills or empties.

The hub is a government building in your capital, and the goods pass through it
as its inputs and outputs. Storing buys from your national market, paid from the
treasury, and adds demand that raises the price. Releasing sells onto your
market, adds supply that lowers the price, and pays the treasury; the journal
entry shows this as Weekly Sales Income.

### Reserve policies and presets

Instead of setting a rate by hand, you can give each good a policy that decides
its rate every week from the national market price, measured against the good's
base price and averaged over several weeks. The gear button in a good's row
opens its settings.

| Policy | What it does |
|---|---|
| Manual | You set the rate. The default for every good. |
| Buy When Cheap | Buys while the averaged price is below your purchase threshold. Never sells. |
| Release When Expensive | Sells while the averaged price is above your release threshold. Never buys. |
| Stabilize Prices | Does both. |

Eight settings shape a policy, and three presets fill them all in one click:

| Setting | Conservative | Standard | Aggressive |
|---|---|---|---|
| Buy below base price by | 20% | 10% | 5% |
| Release above base price by | 30% | 20% | 10% |
| Maximum weekly flow | 2% of capacity | 5% of capacity | 12% of capacity |
| Weekly purchase budget, per good | 0.1% of weekly GDP | 0.3% of weekly GDP | 0.8% of weekly GDP |
| Price memory | 8 weeks | 4 weeks | 2 weeks |
| Response ramp | 20 points | 10 points | 5 points |

Every preset uses the whole capacity: a protected stockpile of 0% and a target
stockpile of 100%. Set those two yourself if you want a floor the policy never
sells. The response ramp spreads the reaction out: the flow rises from nothing
at the threshold to the maximum that many points beyond it. At 0 the policy is a
switch that runs at full flow once the price crosses the threshold.

A preset keeps its flow and budget in step with your country, recalculating them
every week from your capacity and GDP, until you change either by hand. The
preset in force is grayed out, and changing any setting by hand ends it. The
budget is an estimate and a cap for each week; what goes unspent doesn't carry
over. A new reserve starts every good on Manual with the Standard settings
loaded, so switching a good to a policy works at once. The row's own buttons and
Reset Reserve Rates switch goods back to Manual. Policies keep running while the
journal entry is closed.

### Moving or losing the reserve hub

The hub always follows your capital. If your capital moves, the next weekly
update builds a level-1 hub in the new capital for free and removes the old one.
Your stock moves with it, but the new hub has only one level of capacity plus
your silos, and stock above that capacity is lost. The new hub also hires its
5,000 workers from scratch and trades nothing until it is fully staffed. Expand
it again before you need it.

If a foreign power takes the hub's state, the hub is destroyed, the journal
entry ends and the whole stockpile is lost. You can build a new hub in your
capital, and it starts empty. Since the hub always stands in your capital,
protecting the reserve means keeping your capital state. A revolution or
secession that takes the hub's state also costs you the whole stockpile: your
journal entry ends and its stock is lost, while the rebels keep the building and
move it to their own capital.

### How the AI uses the reserve

Great and major powers value the hub highly, especially in peacetime, and add
silos once any good passes 75% of capacity. An AI reserve runs every good on
Stabilize Prices with the Conservative preset: it buys below −20% and releases
above +30%, and while prices stay low it fills an empty reserve in about a year.
It follows the same rules, limits and costs as yours. It doesn't change policy
for a war, but a war that pushes ammunition past +30% makes AI reserves release
into the spike.

## Wartime demand for munitions

Peacetime armies train with half the base game's ammunition. When an army
mobilizes, Basic Supplies, which no army can switch off, raises its ammunition
use by +300% (+50% in the base game). A mobilized battalion therefore burns four
times its peacetime ammunition, twice the base game's peacetime figure. The mod
removes the extra ammunition that Extra Supplies and Luxurious Supplies add in
the base game, so the supplies you choose no longer change how much ammunition
an army uses. The Basic Supplies tooltip shows the ammunition figure. A few of
the mod's own mobilization options add more on top; see
[Mobilization options](12-military.md#mobilization-options).

The demand follows mobilization rather than war: an army mobilized for a
diplomatic play spikes it even if no war follows, and the demand falls away as
the army demobilizes. Where armies buy most of the ammunition, four times the
demand can push its price to the maximum. Build munitions capacity, stock
ammunition in the Strategic Reserve while it is cheap, or both, before you go to
war.

## New mineral deposits

The mod adds fourteen mine types, from Copper and Bauxite Mines to Lithium, Rare
Earth Metals and Platinum Group Metals Mines, and places their deposits in the
regions that hold them in reality, such as copper in the Atacama and Katanga.
They start undiscovered and turn up over time, as undiscovered resources do in
the base game. Twenty-one state traits for famous mining regions, among them the
Bushveld Igneous Complex, the Central African Copperbelt, the Sudbury Basin and
Bayan Obo, raise the throughput of the mines there. The goods these mines
produce are covered in [The extended timeline](02-timeline.md).
