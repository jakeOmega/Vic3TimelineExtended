# Colonial empires and decolonization

Once the Decolonization technology is researched, holding colonies stops being
free. A country with overseas colonies or colonial subjects gets the Colonial
Empire journal entry, whose Colonial Stability bar drifts downward unless your
rank, laws and programs hold it up. You can spend money, authority and
bureaucracy to slow the drift, integrate colonies into the nation, or let them
go on your own terms before they break away. The Decolonization game rule
controls the system; with it off, the journal entry and its events never appear,
and tiny countries never [collapse](#colonial-collapse-of-tiny-countries).

Decolonization also ends your claims on decentralized nations. Within a month of
researching it, you lose every claim you hold on a state of a decentralized
nation, and a Colonial Claims Renounced notice tells you so. Stake Colonial
Claim is no longer open to you, and a claim that reaches you some other way is
dropped within the month. AI countries lose their claims and stop staking them
too. Claims on other countries' states, such as the ones a conquest leaves you
with or the ones behind
[reunification](09-diplomacy.md#irredentism-and-reunification), stay.

## The Colonial Empire journal entry

Decolonization is a society technology in era 6, the first of the mod's eras.
After you research it, the Colonial Empire entry activates as soon as you hold
either of these:

- An overseas colony: a state that is not a homeland of your cultures, has at
least 100,000 people, lies outside your capital's region and the regions next to
it, and has people of a culture that isn't one of your primary cultures. On top
of that, its average standard of living must be below 80% of your national
average, or one of those cultures must make up more than a tenth of the state
with an average acceptance below 60 there.
- A colonial subject: a Colony or Chartered Company subject, or a Protectorate
that holds overseas land and whose cultures share no heritage with yours.

The regions in that test are large ones: Western Europe, North Africa, India,
Southeast Asia and so on. Neighboring regions don't count as overseas, so for a
capital in Western Europe, North Africa and Eastern Europe are next door.

A great power with a few well-integrated colonies and little international
opposition can hold on; a smaller empire condemned by the big powers usually
can't. Two era 9 technologies, Knowledge Economy and Globalization, add −0.75
and −1.5 a month to the drift, so holding on gets harder as the game goes on.

### The Colonial Empire panels

The journal entry opens with an overview, and the sections below it hold the
detail. While the entry runs it has no status line, because the overview shows
where you stand. An entry that isn't running says why: the empire is secured,
it collapsed less than ten years ago, or you hold no colony or colonial subject.

The same panels appear on the Colonial Empire tab of the Timeline Extended
window, which the button under the sidebar's Map List opens, and a change made
in one shows in the other. The tab is grayed until the journal entry is active; hover
it for what is still missing. It ends with an Open Journal Entry button.

<!-- screenshot: the Colonial Empire overview with the stability bar showing a red stretch, and Why Stability Is Moving open with its bars and the Eligible Territories list expanded -->

The overview's first row shows your [band](#colonial-stability-bands), as an
icon and a name (hover it for the band's modifier), and the three programs, lit
while they run. Below them is the Stability bar. Its solid part and a lighter
stretch show today's value and where the bar will be in 12 months at this
month's rate. The stretch is green while stability rises and red while it
falls, so red is what the next year would cost you. A thin cream line marks
where the next band begins; hover it for how many months away that is. Beside
the bar are the value and this month's change, such as "62% (+0.42/mo)", and an
arrow for its direction. Hover the bar for every term behind the change, and
the value for the projection. The line under the bar reads "Next band", with
the band and its threshold.

In the Solidified band, two more bars count toward winning: "Months at 100"
against 60 and, for a great power, "Months Solidified" against 36, the
requirement of the Imperial Federation Act and the Civilizing Mission Compact.
Last comes a pie of great-power prestige, yours included: the condemning powers'
share in red, the supporters' share in green, the rest in grey. Only the
condemning share counts toward [the two escalations](#great-power-stances-on-colonialism),
and an Isolated or Consensus alert shows beside the pie while one applies. Hover
the pie for every great power's stance.

Every section starts open except the explanations:

| Section | Starts | Shows |
|---|---|---|
| Why Stability Is Moving | Open | A bar for each term that moves the bar: red to the left of the center line for a drain, green to the right for a gain, each on its own scale. Then Base decline, Monthly limit and Projected change. Hover a row for what it holds and its bar's scale. Under them is the Eligible Territories list, collapsed. |
| International Pressure | Open | Your prestige, the condemning and supporting shares, and every great power that condemns or supports you. |
| Colonial Programmes | Open | The three programs, each with its costs, its level out of 3, and a minus and a plus button to lower or raise it. |
| Decolonization | Open | How many territories are eligible, how many a Round Table could accept, and the largest; then the three decisions, each with a Review Options button. |
| History | Open | Charts of Colonial Stability and the Monthly Stability Change. |
| How the Colonial Empire Works | Collapsed | The explanations. |

The Eligible Territories list shows the territories the [decolonization
decisions](#releasing-colonies) can offer, up to eight of them, largest GDP
first; hover "+N more" for the rest. Each row gives the territory's people, the
share of them of your primary cultures (Primary), its standard of living (SoL)
and its GDP. The colony icon at the start of the row is lit when the territory
counts as a colony for the stability bar, through Imperial Overreach and
Colonial Acceptance, and dim when it doesn't. A red figure is the test that
makes it one: a red Primary share means another culture is more than a tenth of
its people and accepted below 60, and a red SoL means its standard of living is
below 80% of your national average while some of its people are of other
cultures. Hover a figure for its threshold. A
territory with a dim icon can still be released. The list updates monthly.

### Colonial stability bands

The Colonial Stability bar runs from 0 to 100 and starts at 50. Once a month it
moves by the sum of everything acting on it, but never by more than 1.67 up or
down, so crossing the whole bar takes at least five years. Where the bar sits
puts you in one of five bands. Each band applies a modifier to the journal
entry, and the lower three also raise your colonial subjects' liberty desire.

| Band | Bar | While in this band |
|---|---|---|
| Solidified | 90 and above | +15% prestige, +15 acceptance for pops living outside their homeland, more loyalists from movements |
| Stable | 65–90 | +75 prestige, +5 acceptance for pops outside their homeland, more loyalists from movements |
| Strained | 40–65 | −25 prestige, a little bureaucracy lost; colonial subjects gain liberty desire |
| Crumbling | 20–40 | −50 prestige, −3% bureaucracy; subjects gain more liberty desire; civil rights movements radicalize |
| Collapsing | below 20 | −100 prestige, −6% bureaucracy, more radicals from movements; subjects gain severe liberty desire; civil rights movements radicalize further |

### What moves colonial stability

Why Stability Is Moving shows the projected change for the month and where it
comes from, in the rows below. Hover the bar itself for every term with its
current value.

| Row | What it contains |
|---|---|
| Base decline | −0.5 a month, always. |
| Laws and events | Your Colonization, Minority Rights, Citizenship, Distribution of Power, State Power, Free Speech and Internal Security laws; Knowledge Economy and Globalization; event modifiers such as Positive Colonial Development (+1 a month) and Colonial Crisis (−1 a month) while they last. |
| Interest Groups | Powerful Landowners +0.3 and Armed Forces +0.2; powerful Intelligentsia −0.4 and Trade Unions −0.3. |
| Rank | +0.3 as a great power, −0.5 as anything else. |
| Programmes | Whatever your running colonial programs are worth. |
| War and Turmoil | −0.5 while at war, −1 during a revolution, and a penalty that grows with national turmoil. |
| Imperial Overreach | A penalty once your colonial states outnumber your other states by more than 1.5 to 1. |
| Great Power pressure | Condemnation and support from great powers (see below). |
| Colonial Acceptance | −0.4 for each colony with a severely unaccepted population, +0.5 for each overseas state where everyone is well accepted. |
| Monthly limit | What the ±1.67 cap removed, if anything. |

Colonial Exploitation and Colonial Resettlement raise the bar; No Colonial
Affairs and Neocolonialism lower it. The harshest minority-rights laws drain it
heavily, even though they make a garrison far stronger. Being a nuclear power
helps a little; the UN's Decolonization Resolution ([UN conventions and
agencies](10-united-nations.md#un-conventions-and-agencies)) and foreign
destabilization ([The covert operations](11-influence.md#the-covert-operations))
hurt.

### Great power stances on colonialism

Each great power can hold an anti-colonial stance, a pro-colonial stance, or
none. Every great power that has researched Decolonization is asked to declare
in the event The Colonial Question, at most once every three years, while any
other country holds an overseas colony. That includes powers with no colonies
of their own and powers whose own Colonial Empire entry has ended. It can
condemn colonialism, stay neutral, or back the colonial powers. Condemning
brings influence and prestige but, for a power that holds colonies, also drains
its own bar and weakens its programs. An AI power without colonies nearly always
condemns; one with colonies leans toward backing them. When a Decolonization
Resolution passes at the United Nations, every great power that voted for it, or
voted against it and then accepted it, takes the anti-colonial stance
automatically.

Each condemning great power costs you about 0.6 a month and each supporter adds
about 0.3, scaled by its prestige against yours: from a quarter as much, for a
power with a quarter of your prestige, up to double. If the condemners together
hold a third of the prestige of all great powers plus you, you lose a further 1
a month; if they hold two thirds, another 2. Two condemning peers that together
hold a third already cost about 2.2 a month; with the base decline, the rest of
your terms must add more than +1 just to keep the bar off its fastest monthly
fall. A dominant empire is hard to isolate; a small one reaches both thresholds
as soon as a few large powers turn on it. The International Pressure section
lists who condemns and who supports you.

## Colonial programs and decolonization decisions

The Colonial Empire panels are where you act: three programs you run at a level
from 0 to 3, and three ways to release colonies. The decisions panel adds the
routes to a permanent empire.

### The three colonial programs

Each program runs at a level from 0 (off) to 3, set with the minus and plus
buttons on its row. Level 3 is the full program and each level is a third of
it: a third of its value to the bar every month, a third of its effects and a
third of its running cost. The bar values below are the base at level 3; your
laws change them, and the row shows what the program adds now and what one more
level would add, with its costs.

| Program | Requirement | Bar, per month at level 3 | Costs and side effects at level 3 |
|---|---|---|---|
| Colonial Development Investment | none | about +0.5 | Colonial Development Spending, a weekly cost of 5% a year of your colonies' GDP for each level, counted as at least 1% of your own GDP. Each step up also costs a one-off half a year of one level's spending. Your lower and middle strata expect a higher standard of living. Industrialists and Petite Bourgeoisie disapprove when you start it. Unincorporated states attract more migrants. |
| Military Garrison | more than 100 authority for each step up | about +1.0 | 100 authority a level for as long as it runs, and 5 infamy when you start it. Infamy decays 20% slower. Small losses of bureaucracy and prestige from army projection, higher borrowing costs, weaker Intelligentsia and Trade Unions. |
| Cultural Assimilation Programme | none | about +0.7 | Each step up costs a one-off quarter of a year of one Investment level's spending. −15% bureaucracy and 100 authority while running. Assimilation and conversion speed up, but movements radicalize more, and colonial states lose some qualifications while it runs. |

Investment's cost follows the size of what you develop, not of your whole
economy. If your colonies produce a tenth of your GDP, each level costs about
0.5% of your GDP a year; a great power with a couple of small colonies pays
little. Raise a program only while the bar can still use it: the bar's change
is capped at about 1.67 a month, and the bar stops at 100, so a level that
pushes the change past the cap, or adds to a full bar that is not falling, is
paid for and does nothing. The Monthly limit row in Why Stability Is Moving
shows how much of the change the cap is cutting off.

Laws pull the programs apart. Outlawed Dissent and the harshest minority-rights
laws strengthen the garrison, while Protected Speech and the Protection and
Affirmative Action minority-rights laws weaken it. Voting franchises strengthen
investment. Assimilatory, Ancestral and Cultural Citizenship and the Cultural
Assimilation minority-rights law strengthen assimilation, and Universal
Citizenship weakens it. The program you run longest also decides how the empire
ends (see [How a colonial empire ends](#how-a-colonial-empire-ends)); a month at
a lower level counts as a third of a month for each level.

### Releasing colonies

The Decolonization section offers three decisions. Each one's Review Options
button opens an event that lists the candidates before anything happens, and each event has a
Reconsider option that releases nothing. A territory is a candidate if it isn't
a homeland of your cultures, has at least 100,000 people and lies overseas by
the same region test; it doesn't have to be poorly accepted.

| Decision | What it releases | What you get |
|---|---|---|
| Release a Colonial Territory | One of up to three candidates, largest first | +1 stability a month for 8 months; the new country starts slightly less friendly. |
| Round Table Conference | One of up to three candidates with no severely unaccepted population; needs more than 200 authority | +1 stability a month for 12 months; Intelligentsia approve, Landowners disapprove; the new country starts friendlier. |
| Planned Full Decolonization | Every candidate at once | The whole list goes; the new countries start resentful. |

<!-- screenshot: the confirmation event for a Round Table Conference, listing three candidate colonies with their state counts and the Reconsider option -->

Each candidate leaves with every connected state of yours that is a homeland of
the same culture; the popup shows how many states each choice gives away. Every
release grants Peaceful Decolonization, a decaying +15% prestige, +50 influence
and −200 authority (five years, or ten after Planned Full Decolonization). Each
new country also shakes every other empire: all other countries running the
Colonial Empire entry take a year of Colonial Crisis, −1 stability a month.

Once the UN charter carries Charter Reform II and the Decolonization Resolution
is in force, the General Assembly can order a referendum in a direct subject
whose liberty desire is 50 or more. You hold it, and the subject leaves with a
chance equal to its liberty desire, or you refuse and pay in standing,
prestige and the loyalty of every subject (see [Supervised
referendums](10-united-nations.md#supervised-referendums)).

### Integrating colonies instead

Common Bonds and two decisions keep colonies for good. The event Common Bonds
fires when an overseas state's whole population is well accepted, and lets you
make it a homeland of your primary cultures; it then stops counting as a colony.

The Imperial Federation Act and the Civilizing Mission Compact are decisions
that complete the journal entry at once. Both need a great power that owns at
least four overseas colonies itself (colonial subjects don't count), Colonial
Exploitation or Colonial Resettlement, 36 consecutive months in the Solidified
band, more than 300 authority and 100 prestige. The Act also wants repressive
minority-rights, citizenship, speech and power laws; the Compact wants liberal
ones and a voting franchise. The decision tooltip lists the accepted laws.

The Mandate System Decision suits a liberal empire in managed decline. It needs
the bar at 65 or more, the Neocolonialism law, a voting franchise, no Outlawed
Dissent and more than 100 authority. It costs 100 authority, easing over five
years (Mandate System Transition), and can be taken only once. It gives a
permanent diplomatic-reputation bonus at a small cost in acceptance, and a year
of Positive Colonial Development.

## How a colonial empire ends

The journal entry ends in one of four ways. The event you get when the empire
holds or collapses depends on the program you ran longest, counting a month at
level 1 or 2 as a third or two thirds of a month, and only a program with more
than 24 months.

| Ending | Condition | Result |
|---|---|---|
| The empire holds | The bar stays at 100 for 60 consecutive months | Permanent Colonial Empire Solidified, plus a permanent modifier for your path if one program dominated. Overseas states where everyone is well accepted become homelands. After Quiet Assimilation every overseas state of 75,000 people or more does, whatever its acceptance; after The Iron Fist Holds none do, and you gain 25 infamy. You can never get the entry again. |
| Federation | You take the Imperial Federation Act or the Civilizing Mission Compact | Imperial Federation from the decision, plus a permanent The Iron Fist (Act) or The Commonwealth Path (Compact). Well-accepted overseas states become homelands. You can never get the entry again. |
| Collapse | The bar reaches 0 | Up to three of your overseas territories, picked at random, become independent with their homeland regions, and they inherit the legacy of your longest program (below). Every colonial subject gains Imperial Collapse Aftershock, a large liberty-desire increase for 20 years, and its relations with you drop by 50. The entry can't return for ten years. |
| Voluntary end | You no longer hold any colony or colonial subject while the bar is above 0 | A decaying boost to diplomatic reputation; the event's wording depends on whether you freed colonies by choice. No lockout: new colonies bring the entry back. |

| Longest program | If the empire holds | If it collapses | The countries you free |
|---|---|---|---|
| Military Garrison | The Iron Fist Holds | The Empire Crumbles | Bloody Decolonization Legacy; they start under autocracy with outlawed dissent, and their relations with you fall by 50 |
| Colonial Development Investment | The Commonwealth Path | Negotiated Withdrawal | Commonwealth Legacy; they start as parliamentary republics with protected speech, and relations rise by 30 |
| Cultural Assimilation Programme | Quiet Assimilation | Negotiated Withdrawal | Cultural Assimilation Legacy; they start with Assimilatory Citizenship, and relations rise by 15 |
| none | The Empire Endures | The Empire Crumbles | no legacy |

The legacy applies to every country the system creates: those you free through
the three decisions, those an event frees as a new country, and those that break
away in a collapse. On top of the legacy, a Round Table adds 25 to relations, a
single release subtracts 10 and Planned Full Decolonization subtracts 25. The
Empire Crumbles also leaves you with Colonial Empire Collapsed, a decaying loss
of prestige and standard of living; Negotiated Withdrawal instead gives the same
decaying diplomatic-reputation boost as a voluntary end.

When a revolution wins, the new government carries the empire on. It keeps the
programs you were running, Colonial Empire Solidified and the path rewards of a
finished empire, and the Imperial Federation and Mandate System modifiers (see
[After a revolution](06-politics.md#after-a-revolution)).

## Decolonization events

Most decolonization events fire for the colonial power while the journal entry
runs: as a subject's liberty desire climbs, when great powers condemn or back
you, when colonies resist, and as the cost of empire tells at home. Repressive
options usually add Colonial Crackdown, which strengthens your garrison but
costs prestige and bureaucracy and gives the Intelligentsia more clout; a war
fought while it lasts can bring on the Conscription Crisis. Conciliatory options
add Decolonization Negotiations or free the colony. With the Neocolonialism law,
four events offer independence on your terms and give you Neocolonial Economic
Concessions. Each event and what triggers it is in [Colonial power event
list](19-appendix-events.md#colonial-power-event-list).

### Former colonies

Every colony freed through this system, through an event, or through the base
game's release actions is marked as a former colony of its old ruler. While that
ruler still runs the Colonial Empire entry and is at least a major power, the
former colony may propose closer ties or demand reparations of a tenth of the
old ruler's yearly revenue, capped at a tenth of its own GDP. For its first 20
years it also faces the questions of a young state: development, borders,
government, alignment and identity. A newly independent country in which one
foreign country owns more than 5% of its GDP faces the Nationalization
Question, and seizing everything can bring a great-power old ruler's fleet. The
events are in [Former colony event
list](19-appendix-events.md#former-colony-event-list).

## Colonial collapse of tiny countries

Once any country has researched Decolonization, a tiny, poor AI country can
collapse. The check runs once a year, and a country qualifies when its
population and its average standard of living are both below one of these
pairs:

| Population under | Standard of living under |
|---|---|
| 100,000 | 6 |
| 200,000 | 5 |
| 300,000 | 4 |
| 500,000 | 3 |
| 1,000,000 | 2 |

It must also be independent, at peace, outside any diplomatic play and not on
the verge of a civil war, and it must hold no subjects, belong to no power bloc
and be bound by no treaty. A country that became independent in the last 20
years, by a release, an independence war or a secession, is exempt, and so is
every player's country.

A collapsing country is annexed by an AI neighbor of its most populous state
whose primary cultures share its heritage, provided that neighbor is at peace
and not a subject. A player's country never absorbs one. With no such neighbor,
the country reverts to decentralized land, unless it owns a company or holds
nuclear warheads, in which case nothing happens that year. Players with a state
in the same strategic region, and player great powers, get a notification.

## How the AI runs its colonies

The AI plays by the same rules and uses the same programs and decisions. Once a
month it reviews its programs. It lowers a program by a level when that level is
wasted (without it, the bar's change would still reach the monthly limit, or the
bar is full and would stay full) or when it can no longer pay for it: in
default, or with weekly income below its expenses for Investment, and short of
authority or bureaucracy for the other two. A program cut for cost stays down
for a year. Otherwise, while the bar's change is below the limit, it raises one
program a level if it can afford the step, preferring the garrison when several
colonies are badly unaccepted. An AI that isn't a great power leans strongly toward Planned Full Decolonization, more
so when three great powers condemn it or three of its colonies are badly
unaccepted. AI great powers are less willing, and no AI plans full
decolonization while two of its colonies are well accepted. In events, AI
empires lean toward negotiation and release, and an AI takes the Imperial
Federation Act or Civilizing Mission Compact whenever it qualifies.
