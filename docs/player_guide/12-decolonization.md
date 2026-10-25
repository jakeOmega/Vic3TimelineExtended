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

- An overseas colony: a state that is not a homeland of your cultures and has
at least 100,000 people, which is separated from your capital, has a distinct
people and is held down. It is separated when it isn't joined to your capital
over land through your own states; a strait joins two states only when both are
homelands of your primary cultures. It has a distinct people when a culture
that shares no heritage trait with any of your primary cultures is more than a
tenth of it. It is held down when it is unincorporated, when that people's
average acceptance there is below 60, or when its average standard of living is
below 80% of your national average. A state where more than half the people are
of your primary cultures is settled land, not a colony.
- A colonial subject: a Colony or Chartered Company subject, or a Protectorate
separated from your capital in the same way, none of whose primary cultures
shares a heritage trait with yours.

This is the test the United Nations used in 1960. France's Algeria and its
Tunisian and Moroccan protectorates, Japan's Korea and Taiwan, and Italy's Libya
are colonies, across the sea from their capitals. Land empires are not: Russia's
Central Asia and China's Tibet are joined to their capitals by land, and leave,
if they leave, by the base game's secessions. Heritage traits are narrow, so a
people you share one with doesn't make a state a colony: Ireland under Britain,
Iceland under Denmark, Ryukyu under Japan, or a country's own islands.

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

<!-- screenshot: the Colonial Empire overview with the stability bar showing a red stretch, and Colonial Holdings open with its territories, their Release buttons and a colonial subject's Release and Dominion buttons -->

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
the band and its threshold. Under it, Colonies and Colonial subjects count what
keeps the entry running; hover the line for both tests.

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
| Colonial Holdings | Open | Your wars of independence, your territories and your colonial subjects, with buttons beside each, then Planned Full Decolonization (see below). |
| Why Stability Is Moving | Open | A bar for each term that moves the bar: red to the left of the center line for a drain, green to the right for a gain, each on its own scale. Then Base decline, Monthly limit and Projected change. Hover a row for what it holds and its bar's scale. |
| International Pressure | Open | Your prestige, the condemning and supporting shares, and every great power that condemns or supports you. |
| Colonial Programmes | Open | The three programs, each with its costs, its level out of 3, and a minus and a plus button to lower or raise it. |
| History | Open | Charts of Colonial Stability and the Monthly Stability Change. |
| How the Colonial Empire Works | Collapsed | The explanations. |

Colonial Holdings shows what keeps the entry running and what you can let go.
Its Territories list holds every territory you could
[release](#releasing-colonies), up to eight rows, largest GDP first; hover
"+N more" for the rest. A release takes the neighbouring states where the same
people are at home, so those states share one row: "Henan +1" is Henan and one
more state that would leave with it. Each row gives the share of its people of
your primary cultures (Primary), its standard of living (SoL) and its GDP,
across all its states; hover the name for the states, the people who would form
the new country and the row's weight on stability. The colony icon at the start
of the row is lit when a state in it counts as a colony, which keeps the entry
running and weighs on the bar through Imperial Overreach and Colonial
Acceptance, and dim when none does. A red figure is the test that makes one a
colony: a red Primary share means a people sharing no heritage with yours is
more than a tenth of a state and accepted below 60, and a red SoL means a
state's standard of living is below 80% of your national average while some of
its people are of other cultures. An unincorporated state counts too; hover the
icon for how many of the row's states are. Hover a figure for its threshold. A
row with a dim icon can still be released, with the Release button at the end
of the row.

While you fight a [war of independence](#wars-of-independence), a Wars of
Independence list sits above the territories: the country fighting you, the
months the war has run (red while your war support in it is 25 or below), the
great powers arming it, and an Open Talks button.

The Colonial Subjects list shows your colonial subjects the same way: the flag,
the name, the kind of subject (hover it for why it counts as colonial), its
liberty desire and its GDP, then a Release and a Dominion button (see [Freeing
colonial subjects](#freeing-colonial-subjects)). Under The Whole Empire is
Planned Full Decolonization. Both lists update monthly, and at once after a
release.

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
| War and Turmoil | −0.5 while at war, a further −0.5 for each war of independence (−0.25 once its accords are signed), −1 during a revolution, and a penalty that grows with national turmoil. |
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
from 0 to 3, a button beside each territory and each colonial subject to let it
go, and Planned Full Decolonization to let them all go. Two decisions offer the
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

Every territory in Colonial Holdings has a Release button. It opens a popup about
that territory alone, which names the people who would form the new country and
how many of your states go with it. The new country is formed by the most
numerous culture whose homeland the territory is or, if none of them lives
there, by its most numerous culture that isn't one of yours, and it leaves with
every connected state of yours that is a homeland of that culture. Choose how it
goes, or reconsider. Reconsider releases nothing, and it is what the popup does
if you leave it unanswered. A territory can be released if it isn't a homeland
of your cultures, has at least 100,000 people, is separated from your capital,
has a distinct people and isn't settled land (more than half its people of your
primary cultures); it doesn't have to be held down. A land of your own
heritage, such as an Australia you rule directly, leaves by the base game's
release or as a dominion instead. Hover Release to see whether a Round Table is
open to it.

| Choice | Needs | What you get |
|---|---|---|
| Grant it independence | nothing | +1 stability a month for 8 months; the new country starts slightly less friendly. |
| Round Table Conference | none of the territory's people severely unaccepted, and more than 200 authority; grayed with the reason otherwise | +1 stability a month for 12 months; Intelligentsia approve, Landowners disapprove; the new country starts friendlier. |
| Planned Full Decolonization, under The Whole Empire | nothing | Every territory goes at once, after a popup that lists them; the new countries start resentful. |

<!-- screenshot: the popup for one territory, with Grant it independence, the Round Table Conference grayed with its reason, and Reconsider -->

One of these popups can wait for an answer at a time; until you answer it, the
other buttons are grayed. A release also grants Peaceful Decolonization, a
decaying +15% prestige, +50 influence and −200 authority for five years (ten
after Planned Full Decolonization). A territory or subject you free while it
lasts doesn't add a second one. Each new country also shakes every other
empire: all other countries running the Colonial Empire entry take a year of
Colonial Crisis, −1 stability a month. An empire carries one such year at a
time: new countries formed before it runs out add nothing to it.

### Freeing colonial subjects

Every colonial subject in Colonial Holdings has a Release and a Dominion button.
Each opens a popup about that subject first, with Reconsider as its default. Both
need it to be your own subject, not one of your subjects' subjects, and not your
enemy in a diplomatic play.

| Button | Needs | What happens |
|---|---|---|
| Release | nothing more | The subject becomes independent, a former colony of yours. Relations rise by 30, the Landowners strongly disapprove, and you gain +1 stability a month for 8 months and ten years of Peaceful Decolonization. With the Neocolonialism law you can instead free it on your terms: it takes Neocolonial Dependency, you take Neocolonial Economic Concessions, and relations fall by 10. |
| Dominion | a Colony that can become a dominion, and no change of its autonomy by you lately | It becomes a Dominion, as with the base game's Increase Autonomy: its liberty desire falls by 30 and you take a five-year truce with it. A dominion isn't a colonial subject, so it stops keeping the entry running and your band no longer raises its liberty desire. It still joins your wars, and it may start diplomatic plays of its own. |

A chartered company or a protectorate has no looser kind of subject to become,
so its way out is independence. Letting go of your last colony or colonial
subject ends the entry (see [How a colonial empire ends](#how-a-colonial-empire-ends)).

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

## Wars of independence

A colony can declare its independence, and you can let it go, negotiate, or
fight to keep it. Fighting is hard to win, and winning buys years, not a
settlement: the people are as unaccepted as they were.

### When a colony declares independence

Once your bar is below 40, a colony with severely unaccepted people (acceptance
below 20) may declare independence in Declaration in (the territory), twice as
often below 20. The one most likely to rise goes first: the colony with the
largest share of severely unaccepted people, then the largest. Outside a
collapse, you face at most one declaration every two years, and a territory
that declared, or that you won back, waits ten years before it declares again.
Below 40, Blood in the Colonies also turns its suppression into a war of
independence; at 40 or above it stays a police action.

The popup names the territory, the people who would form the new country and,
when your own people are a tenth or more of the territory, its settlers.

| Choice | What happens |
|---|---|
| Let them go | The country forms now, as in Blood in the Colonies' release: Colonial War Weariness, the Armed Forces disapprove, the Intelligentsia approve, five months of +1 stability. |
| Negotiate the handover | A Round Table release with the declared government as your partner, whatever its acceptance: +1 stability a month for 12 months and friendlier relations. It costs 100 authority, easing over a year. Under Neocolonialism it goes on your economic terms instead. |
| Send the army | The rebels form as a country with the territory and the neighbouring states where its people are at home. The next day they open a diplomatic play against you, and about three weeks later you are at war. Until then you can still back down, which lets them go. You can fight three such wars at once; with three running the option is grayed. |

### Fighting a war of independence

The rebels start the war, a War of Independence. Their goal is Colonial
Independence; yours, Reconquer, annexes them back. Neither costs infamy, and
neither side can add goals. Holding their land doesn't end it: only a
capitulation or a peace does, so a war can drag on long after your army holds
every province.

The rebels fight like guerrillas. They lose less morale and fewer provinces
after a defeat, defend their own provinces better, raise twice the conscripts
and train them faster, and their war support gains "Fighting for independence"
(+0.5 a week), or more with foreign arms. Yours loses "A war to keep a colony"
(−0.25 a week) and "The world condemns it" (−0.25, or −0.5 once the condemning
great powers hold two thirds of great-power prestige), and gains "Settlers to
defend" (+0.25) when your own people are a tenth of the territory. Each war
drains the bar by 0.5 a month on top of the at-war term. Every year of war,
summed over all your wars of independence, costs 2 legitimacy, up to 10. Each
year the Intelligentsia and the Trade Unions disapprove; the Armed Forces
approve for two years, then turn on the government.

A colonial subject's independence war against you, and the secession of a
colony, count as wars of independence too: they appear in the list, the subject
or the secessionists fight with the same advantages, and they end the same way.
Talks are only for a territory's rebels; you make peace with a subject or with
secessionists from the peace screen.

### How a war of independence ends

| Ending | When | You get | The territory |
|---|---|---|---|
| Order Restored | The rebels capitulate or are annexed, or a subject that fought you is still yours when its war ends | 12 months of +1 stability, 12 months on Military Garrison's record (your ending leans toward The Iron Fist), the Armed Forces approve, the Intelligentsia disapprove | Yours again, with large radicals, and no declaration from it for ten years |
| The Flag Comes Down | The war ends and the rebels are free | The Flag Came Down: −15% prestige and −10 legitimacy, decaying over five years; the Armed Forces strongly disapprove for three years and The Veterans' Protest can follow; 12 months of −1 stability | A former colony with Bloody Decolonization's legacy, whatever program you ran: autocracy, outlawed dissent and relations −50 |
| The Accords | Talks dropped your claim and the war ended in a peace | The Accords: −15% prestige and −5 legitimacy, decaying over five years (no legitimacy under the general's mandate); the Armed Forces disapprove for a year | A former colony with your longest program's legacy and a Round Table's friendlier relations |

### Talks and the home front

Open Talks on a war's row asks for a popup first. Talks take six months while
the fighting goes on. When the accords are signed, your claim is dropped: the
rebels take a white peace, and you offer one from the peace screen. An AI opens
talks after half a year of war support in the red, or after four years.

A war that has run four years, with your war support in it at 25 or below for a
year running, breaks the home front. Without a voting franchise, junior
officers rise in The Captains' Revolt: step aside, and talks open on every war,
every territory you could release goes, and the country gets universal
suffrage and a parliamentary republic (a monarchy keeps its crown); or crush
the officers, at −20 legitimacy for two years, and face them again a year
later. With one, it is The Republic in Danger: call the general, who brings a
presidential republic, +100 authority for three years and a peace by the
accords that costs no legitimacy; or hold the line at −15 legitimacy.

### The world takes sides

When a war of independence starts, every great power hears of it. One that
condemns colonialism decides in War in (the territory): condemn it (relations
−20), arm the rebels (they fight harder and keep their resolve, it pays them a
monthly sum, and relations fall by 30), intervene, or stay out. Intervening
joins the war on the rebels' side and is rare: it is open only to a great power
at peace that is your rival with the larger army, and never to your ally,
defensive-pact partner, power bloc partner, subject or overlord, or one under a
truce with you. A great power that backs colonial rule may send you arms
instead, for two years, but never joins the war.

## How a colonial empire ends

The journal entry ends in one of four ways. The event you get when the empire
holds or collapses depends on the program you ran longest, counting a month at
level 1 or 2 as a third or two thirds of a month, and only a program with more
than 24 months.

| Ending | Condition | Result |
|---|---|---|
| The empire holds | The bar stays at 100 for 60 consecutive months | Permanent Colonial Empire Solidified, plus a permanent modifier for your path if one program dominated. Overseas states where everyone is well accepted become homelands. After Quiet Assimilation every overseas state of 75,000 people or more does, whatever its acceptance; after The Iron Fist Holds none do, and you gain 25 infamy. You can never get the entry again. |
| Federation | You take the Imperial Federation Act or the Civilizing Mission Compact | Imperial Federation from the decision, plus a permanent The Iron Fist (Act) or The Commonwealth Path (Compact). Well-accepted overseas states become homelands. You can never get the entry again. |
| Collapse | The bar reaches 0 | Up to three of your territories declare independence, the one most likely to rise first, two months apart, and you can let each go, negotiate or [fight](#wars-of-independence); those that go inherit the legacy of your longest program (below). Every colonial subject gains Imperial Collapse Aftershock, a large liberty-desire increase for 20 years, and its relations with you drop by 50. The entry can't return for ten years. |
| Voluntary end | You no longer hold any colony or colonial subject while the bar is above 0 | A decaying boost to diplomatic reputation; the event's wording depends on whether you freed colonies by choice. No lockout: new colonies bring the entry back. |

| Longest program | If the empire holds | If it collapses | The countries you free |
|---|---|---|---|
| Military Garrison | The Iron Fist Holds | The Empire Crumbles | Bloody Decolonization Legacy; they start under autocracy with outlawed dissent, and their relations with you fall by 50 |
| Colonial Development Investment | The Commonwealth Path | Negotiated Withdrawal | Commonwealth Legacy; they start as parliamentary republics with protected speech, and relations rise by 30 |
| Cultural Assimilation Programme | Quiet Assimilation | Negotiated Withdrawal | Cultural Assimilation Legacy; they start with Assimilatory Citizenship, and relations rise by 15 |
| none | The Empire Endures | The Empire Crumbles | no legacy |

The legacy applies to every country the system creates: those you release from
Colonial Holdings, those an event frees as a new country, and those that go in a
collapse. A colony that wins a war of independence takes Bloody Decolonization's
legacy instead, whatever program you ran. On top of the legacy, a Round Table adds 25 to relations, a
single release subtracts 10 and Planned Full Decolonization subtracts 25. The
Empire Crumbles also leaves you with Colonial Empire Collapsed, a decaying loss
of prestige and standard of living; Negotiated Withdrawal instead gives the same
decaying diplomatic-reputation boost as a voluntary end.

When a revolution wins, the new government carries the empire on. It keeps the
programs you were running, Colonial Empire Solidified and the path rewards of a
finished empire, the Imperial Federation and Mandate System modifiers, and any
war of independence it is still fighting (see
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

The AI plays by the same rules and uses the same programs. It releases a
territory through decisions that offer it the most populous candidates, by grant
or at a Round Table, and frees subjects through events; the buttons beside each
territory and subject are yours. Once a month it reviews its programs. It lowers a program by a level when that level is
wasted, or when it can no longer pay for it: in default, or with weekly income
below its expenses, for Investment; short of authority or bureaucracy for the
other two. A level is wasted when, without it, the bar's monthly change would
still reach the monthly limit, or, with the bar full, would still be +0.5 or
more. That margin keeps a full bar full through a new war. A program cut for
cost stays down for a year. If it lowered nothing, the AI raises one program a
level while the change is below the limit (below +0.5 with the bar full) and it
can afford the step, preferring the garrison when several colonies are badly
unaccepted.

At a declaration, an AI weighs its rank, the condemning great powers and its
other wars. A great power with settlers in the territory, a powerful army lobby
and no voting franchise fights about two times in three; a democratic great
power with no settlers and two condemners about one time in four. A country
that isn't a great power is much less likely to fight, and one in default or
already at war with a great power never does.

An AI that isn't a great power leans strongly toward Planned Full Decolonization,
more so when three great powers condemn it or three of its colonies are badly
unaccepted. AI great powers are less willing, and no AI plans full
decolonization while two of its colonies are well accepted. In events, AI
empires lean toward negotiation and release, and an AI takes the Imperial
Federation Act or Civilizing Mission Compact whenever it qualifies.
