# The space race

The space race is a sequence of journal entries in which great and major powers
compete to reach space milestones, from a first suborbital flight to colonies in
the Kuiper Belt. The first country to finish each of the seven single-goal
milestones keeps a larger permanent reward than anyone who follows. The entries
start to appear once you research Rocketry in era 6, but you need a Space
Program building, unlocked by Guided Missiles in era 7, before any of them can
make progress. The Space Race game rule controls the system; with it off, the
journal entries and their events never appear.

## Joining the space race

Only great powers and major powers can run a space program. If you drop below
major power, your running milestones stop and their progress is lost. The one
exception is Solar System Colonization once you hold a colony: it keeps running
whatever your rank. A player country of either rank always makes progress. An AI
country makes progress only while it is in the top three of the global country
ranking, so in practice you race against the AI powers that hold those places.

### The Space Program building

The Space Program is a monument you build in your market capital, and every
milestone depends on it. It is a single, government-built building with a very
high construction cost. It is removed if the state stops being your market
capital, for example when you lose it in a war. It employs 40,000 engineers,
academics and clerks and consumes Launch Capacity, the good your Aerospace
Industry makes.

Its production method decides which milestones you can run. Each method includes
everything the ones before it allow, so you only ever need the highest one your
program calls for. Each step up uses far more Launch Capacity and gives more
innovation, innovation cap and prestige.

| Production method | Technology | Milestones it allows | Launch Capacity used |
|---|---|---|---|
| Earth Orbit | Guided Missiles (with the building) | Suborbital Flight, Orbital Flight | 500 |
| Moon Mission | Space Exploration | adds Moon Landing and Deep-Space Probe | 1,500 |
| Mars Mission | Knowledge Economy | adds Mars Landing and Moon Base | 5,000 |
| Solar Colonization | Directed Energy Weapons | adds Solar System Colonization, stages 1 and 2 | 25,000 |
| Deep Space Exploration | Space Colonization | lets a country with no colony start colonizing at stages 3 to 5 | 50,000 |
| Interstellar Mission | Muon-Catalyzed Fusion Reactors | adds the Interstellar Probe | 100,000 |

> Lowering the production method, or losing the building, fails every running
> milestone the new method no longer supports and wipes its progress. The event
> Program Discontinued (or The Silent Gantry, if the building is gone) lists what
> was lost. Solar System Colonization only pauses once you hold a colony.

## Space race milestones

There are nine space race journal entries: seven milestones with a single goal,
the repeatable Solar System Colonization, and a waiting entry that follows the
interstellar probe. Each entry appears, inactive, once you have finished the
milestone before it and researched its technology, and it starts when your Space
Program runs a method that supports it.

| Milestone | Needs completed | Technology | Progress needed | Setback risk | Cost factor |
|---|---|---|---|---|---|
| Suborbital Flight | nothing | Rocketry (era 6) | 50 | 5% | ×1 |
| Orbital Flight | Suborbital Flight | Guided Missiles (era 7) | 100 | 6% | ×1.5 |
| Moon Landing | Orbital Flight | Space Exploration (era 7) | 200 | 6% | ×2 |
| Deep-Space Probe | Moon Landing | Space Exploration (era 7) | 150 | 6% | ×2 |
| Mars Landing | Moon Landing | Knowledge Economy (era 9) | 450 | 9% | ×6 |
| Moon Base | Moon Landing | Reusable Rocketry (era 10) | 300 | 8% | ×5 |
| Interstellar Probe | Deep-Space Probe and Mars Landing | Muon-Catalyzed Fusion Reactors (era 12) | 600 | 9% | ×12 |
| Interstellar Probe: Awaiting Data | Interstellar Probe | none | 132 months | none | none |
| Solar System Colonization | Moon Base and Mars Landing | Directed Energy Weapons (era 11) | 400 to 650 per colony | 10% | ×8 |

The setback risk is the base chance each month; the cost factor scales the
milestone's innovation cost (see [Space race funding and
cost](#space-race-funding-and-cost)). The order is mostly a chain, but it
branches after the Moon Landing: the Deep-Space Probe, Mars Landing and Moon
Base can then run at the same time, as long as you have their technologies and
the Mars Mission method. The Interstellar Probe and Solar System Colonization
each need two of those three finished. The Deep-Space Probe and Mars Landing
show up in the journal as soon as you reach orbit and have their technologies,
but neither can start before the Moon Landing.

<!-- screenshot: the Moon Landing journal entry with its milestone panel open, showing progress, pace, setback risk, the Safe and Ambitious selector and the funding stepper -->

### The space milestone panel

Each running milestone has a panel in its journal entry. It shows progress
against the goal, the pace per month, the current setback risk, the setbacks so
far and a rough estimate of the months left. Hover the progress line to see the
reward for finishing first and for finishing later. The controls are an approach
selector (Safe or Ambitious) and a funding stepper. Two collapsed sections
follow. Who else is racing lists the other powers running the same milestone and
whether its "first" is still unclaimed, but not how far along they are. The
program so far shows how far your own program has come across all nine entries.

A new milestone starts with no approach and funding level 1. Until you pick an
approach it creeps forward at 0.5 a month and never suffers a setback (the
panel shows its risk as 0%), but its funding level is already billed.

### Safe and Ambitious approaches

The approach decides how fast a milestone moves and how often it goes wrong.

| Approach | Effect | Innovation cost |
|---|---|---|
| Safe | −50% setback risk. | One extra funding level's worth. |
| Ambitious | +50% progress. | Two extra funding levels' worth. |

Approach, funding and mission choices apply to your whole program, not to the
milestone they sit on. Their modifiers appear on each milestone's journal entry,
but the game adds them up for your country as a whole: every running milestone
with an approach moves at the same pace, and every milestone's base risk is
scaled by the same total. A Safe approach on one milestone cuts the risk on all
of them, including those on Ambitious, and an Ambitious one speeds up all of
them, including those on Safe. They stack: two Ambitious milestones add +100%
progress, and two Safe ones bring every milestone down to the 1% floor. What
stays with each milestone is its innovation cost and the kind of setback it
suffers, which follows its own approach (see [Space race
setbacks](#space-race-setbacks)). Setback risk never drops below 1% a month or
rises above 50%. The panel's pace and risk figures are the ones the game uses,
so check them after every change.

### Mission profile choices

Thirty days after Orbital Flight, the Moon Landing, the Deep-Space Probe, the
Moon Base or the Mars Landing starts, an event asks you to choose how to fly it.
While that milestone runs, your choice changes the setback risk, and sometimes
the pace, of your whole program, in the same way as an approach. When the
milestone is finished it also decides a reward that fades over ten years.

| Event | Milestone | Options |
|---|---|---|
| Who Flies First? | Orbital Flight | Civilian volunteer (riskier; prestige, cultural pull); military test pilot (lower risk, faster; military research, influence); scientist (a little riskier; research, innovation cap) |
| Where the Eagle Shall Land | Moon Landing | Shackleton Crater (much riskier, faster; research, innovation cap); Equatorial Plain (lower risk; prestige, research); Sea of Tranquility (a little riskier; prestige, cultural pull); far side of the Moon (riskier, faster; research, innovation cap) |
| Where Shall We Send the Probe? | Deep-Space Probe | Venus (riskier; research, space race progress); Mars (lower risk, faster; the most space race progress, prestige); the asteroid belt (much riskier; space race progress, innovation cap) |
| The Purpose of the Base | Moon Base | Scientific outpost (lower risk, faster; research, innovation cap); industrial facility (riskier; Extraplanetary Base throughput, Launch Capacity output); military installation (much riskier; military research, influence, cheaper military goods) |
| The Mars Strategy | Mars Landing | Direct landing (much riskier, much faster; prestige, cultural pull); orbital-first (slightly lower risk, faster; research, Space Program throughput); robotic precursors (lower risk; Extraplanetary Base throughput, innovation cap, and Mars Resource Extraction: research speed, space race progress and cultural pull) |

## Space race funding and cost

Each milestone has its own funding level, from 0 up to your cap. The cap starts
at 3 and rises with technology: eleven space-related technologies from era 7 to
era 11 raise it by 1 each, and four in era 12 raise it by 2 each. Tier V of the
Advanced Research power bloc principle, its highest, adds another level.

Every funding level, on any milestone, adds 0.5 to your monthly pace, and so to
every milestone with an approach. It also raises the Space Program's throughput
by 25%, which makes the building consume more Launch Capacity. Funding and
approach cost weekly innovation: 15 for each funding level, plus 15 for a Safe
approach or 30 for an Ambitious one, multiplied by the milestone's cost factor
from the table above. A Suborbital Flight at funding 1 on Safe costs 30
innovation a week; an Interstellar Probe at funding 3 on Ambitious costs 900.
The Space Program Cost modifier on each journal entry shows the current drain.

Your monthly pace is the sum of your progress sources, raised by your progress
bonuses, and never less than 0.5 once you have chosen an approach.

| Progress source | Monthly progress |
|---|---|
| Space Program: Earth Orbit, or any higher method, fully staffed | +0.5, or +1 |
| Each funding level on each running milestone | +0.5 |
| Space Elevator megaproject, each fully staffed level | +1 |
| SpaceX, Lockheed Martin or Roscosmos company, when prosperous | +0.3 each |
| International Space Partnership, for members that ratify the UN's International Space Cooperation | +0.1 |
| Reusable Rocketry and Space Colonization technologies | +0.2 each |
| Mission choices, probe targets and colony specializations | +0.1 to +0.6 each |

| Progress bonus | Effect |
|---|---|
| Ambitious approach | +50% |
| Stolen Rocket Plans, while your Space Programme Espionage operation runs | +10%, and −10% setback risk |
| Outer Space Treaty terms of International Space Cooperation | +10% for lagging powers, −5% for the leader |
| Advanced Research principle, tier V | +10% |
| Antimatter Engine, each fully staffed level | +5% |
| Nanofabrication Center, each fully staffed level | −1% setback risk |
| Temporary Safety Review, from some failure options | −10%, and −25% setback risk |

The International Space Partnership and Outer Space Treaty figures are those at
Established enforcement (×1); they scale with the UN's enforcement, as its other
convention effects do.

## Space race setbacks

Each month, every running milestone with an approach rolls against its setback
risk. A hit fires an event about that milestone, and what it costs depends on
the approach.

On an Ambitious approach you get a mission failure: an explosion on the pad, a
lost probe, a habitat breach, a computer that aborts the landing. Most options
cost 25% of that milestone's progress, give Space Mission Failure (−2% prestige
and −25 innovation cap, fading over five years) and radicalize some academics.
They also start a six-month safety period during which none of your milestones
can suffer another setback, although they keep moving at full pace; the panel
says the program is inside its post-setback review and shows the risk as 0%. One
option usually adds a Temporary Safety Review, which fades over ten years, and
in some events also switches the milestone to Safe. Another usually presses on
with a further flat loss of progress and more radicals, and no safety period.
Now and then the roll brings An Unexpected Breakthrough instead: no progress is
lost, and the Space Program's throughput rises by 15% for 18 or 24 months.

On a Safe approach you get a minor setback: missing parts, bad weather, a
scandal, a quarrel with a foreign supplier. It costs 15% of the milestone's
progress plus a few points, with no lasting modifier and no safety period. A few
setbacks, on either approach, also cut the Space Program's throughput for some
months.

A setback never ends a milestone; it only costs time. Two things do: dropping
below major power, or losing the production method or building the milestone
needs.

## First-to-finish rewards

When a milestone completes, its event plays and every other recognized country
gets a notice two weeks later, from which it can push its own program by 3
points or congratulate you for better relations. The finisher keeps a permanent
reward. The first country to finish a milestone gets the larger version; anyone
who finishes it later gets the smaller one.

| Milestone | Prestige | Innovation cap | Research speed | Influence | Cultural pull |
|---|---|---|---|---|---|
| Suborbital Flight | +2% / +1% | +25 / +10 | none | none | +10% / +3% |
| Orbital Flight | +3% / +1.5% | +50 / +25 | none | none | +15% / +5% |
| Moon Landing | +5% / +3% | +75 / +35 | +5% / +2% | none | +25% / +10% |
| Deep-Space Probe | +4% / +2% | +50 / +25 | +3% / +1% | none | +15% / +5% |
| Moon Base | +5% / +2.5% | +75 / +35 | +5% / +2% | +5% / +2% | +20% / +8% |
| Mars Landing | +7% / +4% | +100 / +50 | +5% / +2% | none | +30% / +12% |
| Interstellar Probe | +10% / +5% | +100 / +50 | +10% / +5% | +10% / +5% | +25% / +10% |

The first figure is the first-to-finish reward, the second the later one.
Suborbital Flight's completion event also offers a choice: loyalists, or
Suborbital Momentum, an extra copy of the later finisher's reward (+1%
prestige, +10 innovation cap, +3% cultural pull) that fades over two and a half
years. Cultural pull feeds the cultural hegemony competition described in [Where
cultural pull comes from](10-influence.md#where-cultural-pull-comes-from).

## Interstellar probe results

Finishing the Interstellar Probe launches it toward Alpha Centauri and opens
Interstellar Probe: Awaiting Data, which counts down 132 months (eleven years).
Nothing you do shortens the wait. When it ends, the probe reports one of 30
possible discoveries in four categories, and you keep that category's reward
permanently.

| Category | Chance | Discoveries | Reward |
|---|---|---|---|
| Dead worlds and data | 40% | 8 | +3% prestige, +5% research speed, +50 innovation cap |
| Astrophysical wonders | 30% | 7 | +5% prestige, +8% research speed, +75 innovation cap, +10% cultural pull |
| Biological discovery | 20% | 9 | +8% prestige, +12% research speed, +125 innovation cap, +20% cultural pull |
| Intelligence detected | 10% | 6 | +12% prestige, +15% research speed, +200 innovation cap, +30% cultural pull |

Each discovery has its own event, from barren worlds and asteroid maps through
ocean worlds and alien vegetation to the ruins of a dead civilization. If
another country's probe found the same thing first, the event names it and
confirms its discovery; the reward is the same.

## Colonizing the solar system

Solar System Colonization is repeatable. Each time its bar fills, you found a
colony on a random unclaimed world in the current stage. Each world can be
claimed once, by anyone, so every other country racing for colonies competes for
the same 34 sites. A stage opens for everyone once every world in the one before
it has been claimed, and each stage needs more progress per colony.

| Stage | Worlds | Colonies | Progress per colony |
|---|---|---|---|
| 1 | Mars (Valles Marineris, Olympus Mons, Hellas Planitia, Utopia Planitia, Arcadia Planitia) and the asteroids (Ceres, 4 Vesta, 16 Psyche, 2 Pallas, 10 Hygiea) | 10 | 400 |
| 2 | Jupiter's moons (Io, Europa, Ganymede, Callisto, Himalia, Amalthea) and a Venus cloud habitat | 7 | 450 |
| 3 | Mercury and Saturn's moons (Titan, Enceladus, Rhea, Mimas, Iapetus) | 6 | 500 |
| 4 | Uranus's moons (Titania, Oberon, Miranda, Ariel) and Neptune's (Triton, Proteus) | 6 | 550 |
| 5 | The Kuiper Belt and beyond (Pluto-Charon, Eris, Makemake, Haumea, Sedna) | 5 | 650 |

From stage 3, a country that doesn't yet hold a colony needs the Deep Space
Exploration or Interstellar Mission method to start the program; a country that
already holds one carries on through all five stages with Solar Colonization.
Each colony's event offers two specializations, and the one you choose becomes a
small permanent modifier on the journal entry. The options differ by world:
research speed, military research speed, innovation cap, space race progress,
Extraplanetary Base, Fusion Plant or Orbital Solar Collector throughput,
Advanced Materials or Launch Capacity output, cultural pull, influence,
diplomatic reputation or cheaper military goods. Your first colony also brings
the event Beyond the Blue.

The entry stays open for as long as you hold a colony, even if you switch off
the Solar Colonization method, so your colony modifiers are never lost; the
program simply stops until the method returns. Once all 34 worlds are claimed,
Solar System Colonization finishes for the country that took the last one, and
for any other colony holder whose program is still running when its bar next
fills. Finishing grants Interplanetary Trade Networks: +10% prestige, +5%
research speed, +10% influence and +15% cultural pull.

## Space race events

Besides the choice, setback and completion events above, the space race has
yearly events for programs under way. Some are hard science problems, such as
radiation or orbital debris; others are discoveries, such as water on Mars.
Their options add progress to the milestones they concern, usually a few points
and never more than 30, and some also bring loyalists, radicals or better
relations. A handful tie the race to other systems: the SpaceX company, a
Tourism Industry, the United Nations, the Extraplanetary Base and the Space
Elevator. They are listed in [Space race event
list](18-appendix-events.md#space-race-event-list).

## How the AI races

AI great and major powers use the same entries, approaches and funding. Only an
AI in the top three of the global ranking makes progress; a weaker one can open
an entry but its bar doesn't move, and the Who else is racing list leaves it
out. Such an AI winds its funding down to 0 and pays nothing for the approach
it has chosen until it climbs back into the top three. AI great powers prefer
the Ambitious approach, more so when another country is running the same
milestone; AI major powers lean toward Safe. The AI raises funding while it has
innovation to spare and cuts it when innovation runs short.

A revolution's winner continues the old country's program, with its progress
(except progress toward a first colony) and its rewards, and rebels can't start
a program of their own during a civil war; see [After a
revolution](05-politics.md#after-a-revolution).
