# Nuclear weapons

Once you research the Nuclear Weapons technology, a great power can fund a
weapons programme that turns research into warheads. Holding warheads brings a
posture to choose (when you would use them, how ready they stand and who may
launch), a standing bill, the risk of accidents, and crises in which you threaten
others or are threatened. Strikes, civil wars that split an arsenal, and warheads
that go missing follow from the same system. The Nuclear Weapons game rule
controls it and is on by default; with it off the technologies remain, but no
programme, stockpile or nuclear events exist.

## The Nuclear Weapons journal entry

Everything happens in one journal entry, **Nuclear Weapons**. It is active for
any country with a working programme, any country holding a warhead (whatever its
rank), and any country caught up in a nuclear crisis. A country with the
technology but not the standing to build sees it inactive, with a status line
saying what it lacks.

| Panel | Shown when | What it holds |
|---|---|---|
| The Programme | You have a programme | Funding, production rate, time to the next warhead, warheads held |
| Progress bar | Always | Progress toward the next warhead |
| Nuclear Posture | You hold warheads | Doctrine, readiness, launch authority, forces, upkeep, incident exposure, interest-group opinions |
| Nuclear Crisis and Reputation | In a crisis, or once you have a record | The crisis and your moves in it; credibility and pledges |
| Delivery and Defence, Nuclear Powers | Always | Strike and interception ratings; the ten largest arsenals as the world estimates them |

<!-- screenshot: the Nuclear Weapons journal entry for an armed great power, programme panel, progress bar and Nuclear Posture panel in view -->

A power that loses its rank stops building but keeps the entry, its posture, its
upkeep and its accidents. Disarming closes the entry, except during a crisis.

## Building a nuclear arsenal

The programme spends weekly innovation on warheads. It is slow to reach the
first device and much faster afterwards.

### Who can run a weapons programme

You need the Nuclear Weapons technology and one of these:

- Great Power rank.
- Major Power rank and the Intercontinental Ballistic Missiles technology.
- A Nuclear Program Aid treaty article in which a nuclear power helps you, at any rank.

A Nuclear Disarmament article, or the United Nations' non-proliferation regime,
ends the programme; a Nuclear Program Freeze holds funding at zero. Losing the
rank that qualified you zeroes funding the same week.

### Programme funding and warhead production

Funding is a stepper in the programme panel. Each step costs 100 weekly
innovation, taken out of your research, and you can add a step only while your
innovation is above 100. A warhead needs 100 progress.

| Stage | Progress per funding step | Example |
|---|---|---|
| First device | 1 a month | 5 steps (500 innovation a week) finish it in 20 months |
| Series production | 10 a month | 5 steps then build a warhead every 2 months |

A Nuclear Program Aid article doubles the rate, covert sabotage slows it, United
Nations inspections cut it by a quarter, and after any nuclear use every funded
programme gets +25% for five years (The Bomb Has Been Used). Events can bring a
laboratory accident, a discovery with civilian uses, or anti-nuclear protests.

### The first device and the world's reaction

The first country to finish a device gets "Dawn of the Atomic Age", the Nuclear
Power modifier and a burst of loyalists. Later powers get "Our Nuclear Arsenal is
Complete" and the same modifier, which raises prestige, diplomatic play
maneuvers, and leverage generation and resistance.

A later programme is noticed at 75 progress on its first device: the great
powers, its rivals and its neighbours get "Nuclear Proliferation Alert". They can
answer with a public ultimatum (a nuclear power only), a crash programme of their
own, a push for a non-proliferation treaty, acceptance, or covert sabotage (only
with the Covert Warfare rule off). Several answers shave progress off the
proliferator.

Other countries see your arsenal only as an estimate, re-observed yearly at
between 60% and 150% of the true count, and exact after a test or a strike. The
Nuclear Powers leaderboard and the AI use these estimates.

## Keeping a nuclear arsenal

From the week your first warhead exists you pay for it, and a human player gets
"A Standing Deterrent" to say so.

### Nuclear deterrent upkeep

Nuclear Deterrent Upkeep is a weekly expense that scales with GDP. The figures
below are shares of GDP a year; each readiness and investment button shows its
exact weekly cost.

| Item | Cost |
|---|---|
| Custody | About 0.01% per warhead, counting at most 50; half at Recessed |
| Heightened readiness | 0.08–0.2%, rising with arsenal size |
| High Alert | 0.25–0.6%, rising with arsenal size |
| Safeguards | About 0.1% per level |
| Hardening | About 0.16% per level |
| Automatic Retaliation | About 0.16% |
| Cap | About 2% |

### Survivability, reliability and crew strain

The posture panel's Forces section tracks three numbers on a 0–100 scale,
updated monthly, and two investment steppers from 0 to 3.

- Survivability is how much of your force would survive a first strike. It climbs toward a ceiling set by technology (25, plus 15 for Radar, 20 for Intercontinental Ballistic Missiles, 25 for Advanced Submarine Technology and 10 for Missile Defense Systems) only while you pay for hardening, and erodes when you stop.
- Command reliability is how well the chain of command holds. Each safeguards level raises it by about 12; strain, buried incidents and enemy sabotage lower it.
- Crew strain rises 5 a month at High Alert, settles around 40 at Heightened, and falls 6 a month at Routine or Recessed.

Safeguards also make an unapproved launch likelier to be halted and cut the
warheads lost when your arsenal changes hands. Survivability decides how hard you
are to coerce.

### Delivery capability and home defence

A strike lands with the attacker's delivery capability minus the target state's
defence, never below 5% and never above 100%.

| Delivery | Bonus | Defence | Bonus |
|---|---|---|---|
| Nuclear Weapons | +100% | Military Aviation | +25% |
| Intercontinental Ballistic Missiles | +50% | Radar | +25% |
| Hypersonic Weapons | +50% | Missile Defense Systems | +50% |
| Orbital Weapon Platforms | +50% | Directed Energy Defenses | +50% |
| Heightened readiness | +5% | Orbital Weapon Platforms | +50% |
| High Alert | +10% | Non-Proliferation Treaty guarantee (unarmed members) | +5% |

Technology defends every state. A Military Base defends its own state only, by
+2% per level with a Missile Defense Battery or +3% with Directed Energy Point
Defense, and AI planners aim fewer strikes at defended states. Military bases in general
are in [Military and war](12-military.md).

## Nuclear posture

Posture is three separate choices, set in the posture panel. A button you can't
use says why.

### Nuclear doctrine

Doctrine says when your government may strike first against a country you are
at war with. Retaliation is allowed under every doctrine. You can change doctrine
once every two years, and the first choice is free.

| Doctrine | First use allowed when | Standing effect |
|---|---|---|
| No First Use | Never | +10% infamy decay and relations improvement, −10% play maneuvers |
| Existential Deterrence (default) | The enemy's side means to annex or subjugate you, or holds goals on your incorporated states while you are losing | +5% leverage resistance |
| Flexible First Use | Also when you are losing to them, or they hold goals on any incorporated state | +10% leverage resistance, +5% maneuvers, −5% infamy decay |
| Nuclear Compellence | Also when they defied your public ultimatum, or your threat against them has reached Confrontation | +15% maneuvers, +10% leverage generation, +10% infamy generation, −10% relations improvement |
| Nuclear Warfighting | In any war | +20% maneuvers, +10% leverage generation, +20% infamy generation, −10% infamy decay, −20% relations improvement |

Losing means a quarter of your land occupied, or under 35% of battles won after
five significant battles. Adopting Compellence or Warfighting costs 5 infamy and
10 relations with every rival. Leaving No First Use is a **repudiation**: −20
credibility, +10 infamy, a ten-year Broken Nuclear Pledge modifier, and your
restraint-minded interest groups disapprove. While the No-First-Strike Pledge
amendment is on your laws (see [Government, laws and characters](05-politics.md)),
your doctrine is held at No First Use, and leaving it strikes the amendment.

### Nuclear readiness levels

Readiness moves one step every two weeks toward the level you order.

| Readiness | What it means |
|---|---|
| Recessed | Warheads stored apart from their delivery systems. Half the custody cost, half the incidents of Routine, less dangerous crises. Nothing can be launched, not even in retaliation, until you are back at Routine, and your threats carry less weight |
| Routine | The default. Cheap and slow; crews recover |
| Heightened | +5% strike success; incidents four times as likely as at Routine |
| High Alert | +10% strike success and +5 play maneuvers; strain builds every month, and with it accidents and false warnings |

Struck while Recessed, you can order the warheads mated; "Our Forces Are Ready"
offers the answer when they reach Routine, if the war goes on. A stand-down agreed
or conceded in a crisis holds you at Routine or below for two years.

### Launch authority

Launch authority decides who may act when a warning is uncertain. It can change
once a year.

| Authority | Needs | Effect |
|---|---|---|
| Central Authorization | Nothing | Only the government orders a launch |
| Conditional Delegation | Radar | Cut-off commanders may fire. In a war, an incident can end in a launch you never approved |
| Launch on Warning | Radar, Intercontinental Ballistic Missiles | A false warning can become a launch under standing orders |
| Automatic Retaliation | Radar, Intercontinental Ballistic Missiles, Mainframe Computers | A strategic first strike on you is answered in full, up to three warheads, with no choice left to you. Threats against you count as if your forces were survivable. Extra upkeep; restraint-minded groups dislike it; an accident at home during a war or an acute crisis can set it off |

Under delegation or launch on warning, the panel shows the chance that someone in
the chain halts an unapproved launch. Automatic Retaliation never answers a
retaliation, and answers a given attacker at most once in six months.

### How interest groups judge your posture

The At Home section lists each interest group with a view and the approval it
adds: Nuclear Posture: Enthusiastic (+2), Approving (+1), Uneasy (−1) or Opposed
(−2). Opinions are reviewed monthly, and doctrine and readiness count only once a
doctrine has stood for six months.

| Group | Wants | Dislikes |
|---|---|---|
| Armed Forces (officers) | Flexible deterrence at Heightened readiness | No First Use, Warfighting, Recessed, Routine when an armed enemy is plausible, High Alert with strain of 50 or more |
| Industrialists (business) | No doctrine preference | High Alert held three months or more; any crisis at Confrontation or beyond |
| Groups favouring Total War over Limited War | Compellence or Warfighting, High Alert | Routine or Recessed |
| Groups favouring Limited War over Total War | No First Use, Recessed | Compellence, Warfighting, High Alert, Launch on Warning, Automatic Retaliation |

A group that only approves of its preferred Rules of War law, rather than
strongly, holds a mild view (±1). The Armed Forces and the Industrialists also
lean with their leader: a jingoist-led army wants compellence.

### The nuclear umbrella and nuclear guarantees

Your direct subjects are under your **nuclear umbrella** while you hold Nuclear
Power, unless you are at war with them or on opposite sides of a play. Anyone
else needs a Nuclear Guarantee treaty article. Either cover spares the country
the war-support drain of facing a nuclear-armed enemy without the bomb, weighs
your arsenal in any crisis against it, lets you open a crisis against a country
in a war or play with it, and lets you retaliate for a strike on it under any
doctrine. You
are asked to answer when it is threatened or struck (see
[Guarantors called in](#guarantors-called-in)).

Withdraw Nuclear Umbrella is a diplomatic action on a direct subject: +10 liberty
desire and −20 relations at once, then +0.1 liberty desire a week until you
restore it. Subjects of your subjects are covered by their own overlord only, and
power bloc members need a treaty.

Going Recessed while you protect anyone brings "Our Allies Are Alarmed" every
time: −5 credibility, −10 relations with each country you protect, and +5 liberty
desire in each covered subject. A protector in storage counts for half in a
crisis.

## Nuclear crises

A nuclear crisis is one pair of countries and one dispute, with a deadline. The
issuer, the country that made the threat, runs it; the other is the target. A
country can be in only one crisis at a time.

### Opening a nuclear crisis

Two diplomatic actions open one:

| Action | Cost | Deadline |
|---|---|---|
| Private Nuclear Warning | −5 relations | 10 weeks |
| Public Nuclear Ultimatum | +5 infamy, −20 relations, higher reputation stakes | 8 weeks |

Both need an arsenal, both sides free of other crises, no crisis between the two
in the last 24 months (waived in war), no non-use pledge between you, and one of
these disputes, taken in this order:

| Dispute | What the target gives up if it concedes |
|---|---|
| A war between you | −35 war support in that war |
| A diplomatic play between you | The play is settled in your favour |
| An attack on a country you cover | The same, on your protégé's behalf |
| A weapons programme run by your rival, or by a country you are antagonistic, belligerent or domineering toward | Its programme is frozen for 10 years |
| An armed rival at Heightened readiness or higher | It stands down to Routine for 24 months |

### Crisis stages, danger and pressure

A crisis starts at Warning. It becomes a Confrontation when it goes public, is
refused or answered with a counter-threat, or when either side holds an exercise.
A Confrontation turns Acute when danger reaches 70 or the issuer is at High Alert
while the target is at Heightened or higher. Any crisis turns Acute when the
issuer holds firm past its deadline, a play becomes a war, or a launch is
intercepted. A crisis can be settled at any stage, and it lapses after a year.

The crisis panel shows two figures, each broken down in its tooltip.

- Danger (0–100) rises with the stage, time, publicity, readiness, counter-threats and exercises, and falls with open talks. It is lower when the target has no arsenal and no armed protector. High danger makes incidents likelier.
- Pressure on the target (0–100) comes from the issuer's credibility, whether the threat can be carried out, the danger, the war, whether the target can answer in kind, an armed protector behind it, exercises and alerts, and the target ruler's temperament. An AI target never concedes below 50, about half the time from 70 and two times in three from 85.

From Confrontation on, the target is pressed every six weeks unless talks are
open.

<!-- screenshot: the Nuclear Crisis panel during a Confrontation, with the pressure breakdown tooltip open -->

### Moves during a crisis

Each side acts through events and the crisis panel's buttons.

| Move | Who | Effect |
|---|---|---|
| Concede | Target | The concession happens at once and the crisis ends |
| Refuse | Target | Confrontation. A refused public ultimatum counts as defiance, which lets a Compellence issuer strike you in a war |
| Counter-threat | Armed target | Confrontation, danger +10, readiness to Heightened |
| Propose a mutual stand-down | Either | Pressure pauses and danger falls 15 while the other side decides. If accepted, both stand down to Routine for 24 months and pledge non-use; the war or play goes on |
| Go public | Issuer | +5 infamy, −15 relations, a new 8-week deadline |
| Exercise | Either armed side | Money and 5 strain; for six weeks danger +10, and pressure +10 if the issuer holds it. It can be mistaken for an attack |
| Back down | Issuer | The crisis ends in a climb-down |

At the deadline the issuer chooses: six more weeks (−3 credibility), hold firm
(the crisis turns Acute, forces go to High Alert, six more weeks), offer a
stand-down, let it lapse, or, at war with the target and with every strike gate
open, carry out the threat. A play under a public ultimatum that turns into a war
brings "They Chose War": strike, fight conventionally (−10 credibility,
militarists disapprove) or offer a stand-down.

### Credibility, bluffs and crisis outcomes

Doctrine is public, so the panel rates every threat: Backed (+10 pressure; your
doctrine permits a strike now, or you hold Compellence or Warfighting), Uncertain
(Flexible First Use, or Existential Deterrence with something at stake), or A
bluff (−25, or −35 under No First Use; your doctrine or Rules of War law forbids
a strike).

| Outcome | Issuer | Target |
|---|---|---|
| The target concedes | +10 credibility (+15 if public), Nuclear Brinkmanship Rewarded, hawks approve | −5 credibility, Yielded to Nuclear Coercion, hawks disapprove |
| The issuer backs down | −5 credibility if private; −15, Nuclear Climb-Down and angry hawks if public | +10 credibility, Faced Down a Nuclear Threat |
| Mutual stand-down | +5 credibility (−5 for trading away a public demand), Mutual Nuclear Restraint, restraint groups approve | +5 credibility, Mutual Nuclear Restraint, restraint groups approve |
| A public ultimatum lapses | −10 credibility | Nothing |

A public bluff that ends in a climb-down or lapses costs 5 more credibility. The
modifiers last five years. A crisis also ends when its war or play ends, or when
nuclear weapons are used between the two. A non-use pledge from a stand-down
blocks strikes on that partner until one side uses Repudiate Non-Use Pledge (−15
credibility, +5 infamy, −30 relations and a Broken Nuclear Pledge).

### Guarantors called in

When a country you guarantee or cover is warned or struck, you get "A Promise
Called In":

| Choice | Effect |
|---|---|
| Honour | +5 credibility. Under threat, you back the target. After a strike, you join its war, or open a public crisis against the attacker if there is no war to join |
| Retaliate (after a strike) | +10 credibility; you join the war and strike back a day later, as retaliation, under any doctrine |
| Abandon | −15 credibility, Abandoned a Nuclear Guarantee for five years, −30 relations with the protégé and −10 with everyone else you protect; a subject gains 10 liberty desire |

If your protégé used the bomb first and its victim answered, you get "Our Protégé
Struck First" instead. Standing by it or answering in kind costs 5 infamy;
declining costs no credibility, only 10 relations with the protégé.

## Nuclear strikes

Strikes are diplomatic actions against a country you are at war with, aimed at a
state you pick.

### Strategic and tactical strike actions

| | Nuclear Weapon Industrial Strike | Tactical Nuclear Strike |
|---|---|---|
| Needs | Nuclear Power and a warhead | The same, and the Tactical Nuclear Weapons technology |
| Target | Any enemy state | A state with a Barracks, Naval Administration, Naval Fortification, Naval Logistics Center, Conscription Center or Military Base |
| Rules of War that forbid it | Humanitarian Regulations, Limited War | Limited War |

Every strike, including those offered by events, also needs your doctrine to allow
it, no non-use pledge with the target, and forces that are not Recessed. The
Rules of War block lifts once you or a country you cover has been struck, or when
an enemy's war goal would annex or subjugate you.

### What a nuclear strike does

A strategic strike that lands devastates the state, kills a tenth of its people
and leaves Nuclear Strike Aftermath for two and a half years (decaying): −50%
infrastructure, −3 standard of living, +25% mortality and −50% throughput. The
victim loses 12.5 war support and 50 relations with you, and you gain 25 infamy.
A strike that fails costs 5 infamy.

A tactical strike that lands kills half the soldiers and officers in the state
and a few civilians, stops unit training there for a while, and costs 10 infamy.
It halves every Naval Fortification and Military Base in the state, an odd level
lost on a coin flip, so a level-1 site is destroyed half the time. Barracks,
conscription centres and the other naval buildings survive.

Both sides get a notification of the result. Every use speeds up the world's
funded programmes and ends any crisis between the two countries. The United
Nations records it against you, and its court may indict your ruler (see
[The United Nations](09-united-nations.md)).

### Retaliation and Automatic Retaliation

The victim of a strategic strike gets "A City Erased" with its answer: condemn
the attack, retaliate with one warhead, or launch a full retaliation of three if
it holds more than two. Retaliation costs no infamy and counts for less with the
United Nations than a first strike, and the attacker may answer it in turn. Under
Automatic Retaliation the answer is made for you; while Recessed you can only
mate the warheads and answer when they are ready.

## Nuclear incidents and accidents

Every armed country rolls once a month for something going wrong. The base chance
is 0.05% a month at Recessed, 0.1% at Routine, 0.4% at Heightened and 1% at High
Alert, raised by strain, poor reliability and a dangerous crisis, up to 3%. Over
ten years of peace that is roughly a 5–10% chance of any incident at Routine,
40–50% at Heightened and 90% at High Alert.

| Incident | Can happen when | What it is |
|---|---|---|
| The Unconfirmed Warning | Radar, Heightened or higher, and an armed enemy, rival, crisis opponent or hostile country | A false warning of attack. Under Central Authorization or Automatic Retaliation you decide; under delegation in a war, or Launch on Warning, the chain halts it or launches |
| The Exercise They Mistook | A crisis at Confrontation or beyond, Heightened or higher | Your opponent reads your exercise as cover for an attack |
| Silence from the Capital | Delegation or Launch on Warning, not Recessed, in a war or an Acute crisis | A commander cut off from the capital; an officer refuses, or the unit fires |
| The Cost of Permanent Alert | High Alert for six months, or strain of 60 or more | Crashes, silo explosions, lost weapons, a contaminated state |
| A Routine Mishap | Always | False alarms, dropped training weapons, storms |

Most incidents cost money, readiness, reliability or reputation. A buried
incident has a 3% chance each month of coming out (Nuclear
Cover-Up Exposed: −10 legitimacy, −10% authority, −5% prestige).

A launch needs a war with the country in question. Outside a war, a launch nobody
halted is recalled at the last moment: +10 infamy, −50 relations with the target,
more strain and less reliability, and an armed target may answer by opening a
crisis. Under No First Use, even an unapproved launch in a war breaks your
pledge.

### The Monopoly Window

A Compellence or Warfighting power at war with an enemy that has no arsenal and
no armed ally in that war has an 8% chance a month, at most once a year, of "The
Monopoly Window": its general staff proposes using the bomb while nobody can
answer. You can win conventionally, issue a public ultimatum, or authorise the
strike.

## Arsenals in civil wars and annexations

Warheads outlive the government that built them. When an armed country is
annexed by war, diplomacy or a formable nation, its arsenal passes to whoever
holds the most populous state in its old capital's region, and a human recipient
gets "The Arsenal Changes Hands". Every such transfer loses some warheads on the
way: 7% with no safeguards, 2% less per level (1% at level 3), 3% more under
delegation or Launch on Warning, doubled if the holder was at war. **Secured
custody** halves the loss. You have it while a foreign custodian helps you in a
civil war, for twenty years after opening your depots to inspectors over a stolen
warhead, while a Nuclear Security Assistance article is in force, or as a party to
the United Nations convention on protecting nuclear material. Missing warheads
become [loose warheads](#loose-warheads).

### Who Holds the Button?

When a revolution or secession breaks out in an armed country, the government
chooses in "Who Holds the Button?", whose tooltips show the exact numbers:

- Hold the line: the rebels seize a share matching their share of the population, half again more under delegated authority and 20% less per safeguards level, and some of those go missing.
- Bring them in: readiness goes to Recessed and stays locked there until every civil war of yours is over, so you can't strike, answer a strike or raise readiness. Rebels take half their share under delegated authority, none under central control.
- Take them apart: your stockpile goes to zero and you lose Nuclear Power, nothing is seized or lost, and every country's relations with you rise by 10.

Striking your own civil war, from either side, brings Nuclear Weapons Used on
Our Own People (−50 legitimacy, decaying over twenty years) and a wave of
radicals that your speech and policing laws shrink or enlarge.

### When a revolution wins or loses

A winning revolution takes the state's arsenal, less the warheads lost, as a new
regime: it keeps the old doctrine, investments and warhead progress, restarts at
50 credibility, and drops the old government's pledges and crises. If the
government wins, the rebels' warheads come back. A winning secession keeps what
it seized; a crushed one returns it.

### Deny Them the Bomb

A government losing a revolution while armed (a quarter of its land occupied, or
most battles lost) is asked once per civil war, "Deny Them the Bomb". Taking the
warheads apart in haste loses some on the way; an accepted foreign custodian can
take them apart with none lost; or you keep them, and a winning revolution
inherits them. A secession never asks this, because its winner does not take the
government's arsenal.

### Foreign powers and a divided arsenal

A week after an armed country's civil war breaks out, every armed major power and
armed neighbour gets "A Nuclear Power Divided". It can back either side (+20
relations with it, −20 with the other, +5 war support for that side), offer to
secure the arsenal, or stay out. An accepted offer makes the helper the
government's custodian for the war.

### The Budapest path

A week after a secession wins while holding warheads, every armed great power
gets "A New Nuclear State" and may press it. A month after the first does, the new
state gets "The Budapest Offer". Trading the warheads away dismantles them: the
pressing power with the largest economy signs a Nuclear Disarmament and a Nuclear
Guarantee, every other presser adds a guarantee, all binding for ten years, and
relations with each rise by 20. Keeping them costs 20 relations with each
presser, and for ten years the AI is much readier to demand disarmament.

## Loose warheads

Lost warheads stay in the world. The posture panel's Unaccounted for row counts
those from your arsenal.

### Nuclear terror plots

Once warheads are loose, a plot can come up in the yearly terror events of a
country with the Terrorism and Antiterrorism technology and at least 10%
radicals, a war, or a movement with radicalism of 25 or more. It is real with a
20% chance per loose warhead in the world (at most 80%), using another country's
lost warheads. Your security services seize it first with a 10% chance, plus 5%
per Ministry of Intelligence and Security level and 15% with the Nuclear Weapons
technology (at most 75%). Otherwise it destroys a city in one of your populous
states. The world sees at most one plot a year.

### Tracing a stolen warhead

A month later, "Where Did It Come From?" reports the result. Your own nuclear
expertise, a covert network in the country of origin, a seized device and fewer
possible sources make certainty likelier.

| Finding | Your options |
|---|---|
| Confirmed | Hold the origin to account |
| A shortlist of two or three, which may include innocent countries | Name them all in public (−25 relations with each), or ask each privately to open its depots |
| Unknown | Say nothing, or blame a rival anyway |

Blame means negligence, not attack. The origin gets "The Warhead Was Ours" and can
pay compensation (up to a tenth of your GDP), let your inspectors in (twenty years
of secured custody, Custody Inspections at −5 legitimacy, and a 50% chance of
finding one of its missing warheads at once), or deny it (−40 relations, +5
infamy).

### Recovering loose warheads

Recovered warheads are destroyed. Besides the inspection search, three things
find them:

- Covert: Secure Loose Material, an operation against a country with warheads missing: a 3% chance a month once established, 6% when fully operational (see [Cultural hegemony and covert warfare](10-influence.md), which also covers Covert: Nuclear Programme Sabotage).
- A Nuclear Security Assistance article: 6% a month for the country helped.
- The United Nations convention on protecting nuclear material: 3% a month for each party. It reaches the Assembly only once warheads have gone missing somewhere.

## Nuclear treaty articles

Five treaty articles deal with nuclear weapons.

| Article | Parties | Effect |
|---|---|---|
| Nuclear Disarmament | The disarmed country concedes; the demander pays 200 influence | Stockpile and progress go to zero, Nuclear Power is lost, and no programme runs while it lasts |
| Nuclear Program Freeze | The frozen country concedes; the demander pays 100 | Funding held at zero; warheads and progress kept |
| Nuclear Program Aid | A nuclear power helps a non-nuclear country and pays 500 | The recipient can run a programme at any rank, at double the rate. Refused once the IAEA exists and United Nations authority is 60 or more |
| Nuclear Guarantee | An armed guarantor pays 100 | Extended deterrence, as for the umbrella; not for your own subjects |
| Nuclear Security Assistance | An armed country pays 100 to help one holding or missing warheads | Secured custody and a monthly chance to recover missing warheads |

Aid can't be combined with a disarmament or freeze of the same country. The
United Nations' non-proliferation treaty and IAEA are in
[The United Nations](09-united-nations.md).

## How the AI plays nuclear weapons

- It funds its programme toward a target stockpile that grows with rank, innovation, war and a rival that seems to hold more.
- It reviews its posture every six months and when a crisis opens. Most AIs keep Existential Deterrence; cautious rulers and democracies lean to No First Use, and militarist regimes (fascist, or with a jingoist ruler or a powerful Armed Forces in government) to Compellence or Warfighting.
- It goes to High Alert in an Acute crisis or a war with an armed enemy, to Heightened in any war or Confrontation, and to Recessed only at peace with nothing to deter and nobody to protect.
- It strikes first only when its doctrine allows and its survival is at stake, or when it is losing (Flexible), was defied (Compellence) or is at war (Warfighting) against an enemy with no arsenal and no armed protector. It keeps a warhead in reserve unless its survival is at stake, waits six months between first uses, and strikes its own rebels only with 40% of its land occupied under Outlawed Dissent or a Secret Police.
- It warns countries that threaten a protégé or its survival; coercive warnings need a hawkish doctrine or regime and a target that can't answer. It never makes a public bluff.
- It usually declines to answer for a protégé that struck first, never withdraws a nuclear umbrella, and demands disarmament from rivals and hostile countries.
