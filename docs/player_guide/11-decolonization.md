# Colonial empires and decolonization

Once the Decolonization technology is researched, holding colonies stops being
free. A country with overseas colonies or colonial subjects gets the Colonial
Empire journal entry, whose Colonial Stability bar drifts downward unless your
rank, laws and programs hold it up. You can spend money, authority and
bureaucracy to slow the drift, integrate colonies into the nation, or let them
go on your own terms before they break away. The Decolonization game rule controls the system; with it off, the
journal entry and its events never appear.

## The Colonial Empire journal entry

Decolonization is a society technology in era 6, the first of the mod's eras.
After you research it, the Colonial Empire entry activates as soon as you hold
either of these:

- An overseas colony: a state that is not a homeland of your cultures, has at
  least 100,000 people, lies outside your capital's region and the regions next
  to it, and has people of a culture that isn't one of your primary cultures.
  On top of that, its average standard of living must be below 80% of your
  national average, or one of those cultures must have almost no acceptance
  there.
- A colonial subject: a Colony or Chartered Company subject, or a Protectorate
  that holds overseas land and whose cultures share no heritage with yours.

The regions in that test are large ones: Western Europe, North Africa, India,
Southeast Asia and so on. Neighboring regions don't count as overseas, so for a
capital in Western Europe, North Africa and Eastern Europe are next door.

A great power with a few well-integrated colonies and little international
opposition can hold on; a smaller empire condemned by the big powers usually
can't. Two era 9 technologies, Knowledge Economy and Globalization, add −0.75
and −1.5 a month to the drift, so holding on gets harder as the game goes on.

<!-- screenshot: the Colonial Empire journal entry with the Colonial Stability widget open, showing the band headline, the monthly breakdown and the three program rows -->

### Colonial stability bands

The Colonial Stability bar runs from 0 to 100 and starts at 50. Once a month it
moves by the sum of everything acting on it, but never by more than 1.67 up or
down, so crossing the whole bar takes at least five years. Where the bar sits
puts you in one of five bands. Each band applies a modifier to the journal entry,
and the lower three also raise your colonial subjects' liberty desire.

| Band | Bar | While in this band |
|---|---|---|
| Solidified | 90 and above | +15% prestige, +15 acceptance for pops living outside their homeland, more loyalists from movements |
| Stable | 65–90 | +75 prestige, +5 acceptance for pops outside their homeland, more loyalists from movements |
| Strained | 40–65 | −25 prestige, a little bureaucracy lost; colonial subjects gain liberty desire |
| Crumbling | 20–40 | −50 prestige, −3% bureaucracy; subjects gain more liberty desire; civil rights movements radicalize |
| Collapsing | below 20 | −100 prestige, −6% bureaucracy, more radicals from movements; subjects gain severe liberty desire; civil rights movements radicalize further |

### What moves colonial stability

The widget's Colonial Stability section shows the projected change for the month
and where it comes from, in the groups below. Hover the bar itself for every
term with its current value.

| Group | What it contains |
|---|---|
| Base imperial decline | −0.5 a month, always. |
| Laws, technologies and recent events | Your Colonization, Minority Rights, Citizenship, Distribution of Power, State Power, Free Speech and Internal Security laws; Knowledge Economy and Globalization; event modifiers such as Positive Colonial Development (+1 a month) and Colonial Crisis (−1 a month) while they last. |
| Domestic interest groups | Powerful Landowners +0.3 and Armed Forces +0.2; powerful Intelligentsia −0.4 and Trade Unions −0.3. |
| Rank and standing | +0.3 as a great power, −0.5 as anything else. |
| Active programs | Whatever your running colonial programs are worth. |
| War, revolution and turmoil | −0.5 while at war, −1 during a revolution, and a penalty that grows with national turmoil. |
| Imperial overreach | A penalty once your colonial states outnumber your other states by more than 1.5 to 1. |
| Great power pressure | Condemnation and support from great powers (see below). |
| Colonial acceptance | −0.4 for each colony with a severely unaccepted population, +0.5 for each overseas state where everyone is well accepted. |
| Monthly limit | What the ±1.67 cap removed, if anything. |

Colonial Exploitation and Colonial Resettlement raise the bar; No Colonial
Affairs and Neocolonialism lower it. The harshest minority-rights laws drain it heavily, even
though they make a garrison far stronger. Being a nuclear power helps a little;
the UN's Decolonization Resolution ([The United Nations](09-united-nations.md))
and foreign destabilization ([Cultural hegemony and covert warfare](10-influence.md))
hurt.

### Great power stances on colonialism

Each great power can hold an anti-colonial stance, a pro-colonial stance, or
none. A great power that runs the Colonial Empire entry itself is asked to
declare in the event The Colonial Question, at most once every three years: it
can condemn colonialism, stay neutral, or back the colonial powers. Condemning
brings influence and prestige but, for a power that holds colonies, also drains
its own bar and weakens its programs. When a Decolonization Resolution passes
at the United Nations, every great power that voted for it, or voted against
it and then accepted it, takes the anti-colonial stance automatically. That is
how powers without colonies usually end up condemning yours.

Each condemning great power costs you about 0.6 a month and each supporter adds
about 0.3, scaled by its prestige against yours: from a quarter as much, for a
power with a quarter of your prestige, up to double. Two further penalties apply
when the condemners together hold a third (−1 a month) and then two-thirds
(another −2) of the prestige of all great powers plus you. A dominant empire is
hard to isolate; a small one reaches both thresholds as soon as a few large
powers turn on it. The widget's International Pressure section lists who
condemns and who supports you.

## Colonial programs and decolonization decisions

The Colonial Empire widget is where you act: three programs you switch on and
off, and three ways to release colonies. The decisions panel adds the routes to
a permanent empire.

### The three colonial programs

Each program has an Enable and a Disable button and adds its value to the bar
every month it runs. The values below are the base; your laws change them, and
the program row shows your current figure with its costs.

| Program | Requirement | Bar, per month | Costs and side effects |
|---|---|---|---|
| Colonial Development Investment | none | about +0.5 | One-off payment of 2% of GDP, then Colonial Development Spending, a running cost that scales with GDP. Your lower and middle strata expect a higher standard of living. Industrialists and Petite Bourgeoisie disapprove. Unincorporated states attract more migrants. |
| Military Garrison | more than 300 authority | about +1.0 | Costs 300 authority for as long as it runs and 5 infamy when started. Infamy decays 20% slower. Small losses of bureaucracy and prestige from army projection, higher borrowing costs, weaker Intelligentsia and Trade Unions. |
| Cultural Assimilation Programme | none | about +0.7 | One-off payment of 1% of GDP, −15% bureaucracy and 100 authority while running. Assimilation and conversion speed up, but movements radicalize more, and colonial states lose some qualifications while it runs. |

Laws pull the programs apart. Outlawed Dissent and the harshest minority-rights
laws strengthen the garrison, while Protected Speech and the Protection and
Affirmative Action minority-rights laws weaken it. Voting franchises strengthen
investment. Assimilatory, Ancestral and Cultural Citizenship and the Cultural
Assimilation minority-rights law strengthen assimilation, and Universal
Citizenship weakens it. The program you run longest also decides how the
empire ends (see [How a colonial empire ends](#how-a-colonial-empire-ends)).

### Releasing colonies

The widget's Decolonization section offers three decisions. Each one opens an
event that lists the candidates before anything happens, and each event has a
Reconsider option that releases nothing. A territory is a candidate if it isn't a
homeland of your cultures, has at least 100,000 people and lies overseas by the
same region test; it doesn't have to be poorly accepted.

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

### Integrating colonies instead

Common Bonds and two decisions keep colonies for good. The event Common Bonds
fires when an overseas state's whole population is well accepted, and lets you
make it a homeland of your primary cultures; it then stops counting as a
colony.

The Imperial Federation Act and the Civilizing Mission Compact are decisions that
complete the journal entry at once. Both need a great power that owns at least
four overseas colonies itself (colonial subjects don't count), Colonial
Exploitation or Colonial Resettlement, 36 consecutive months in the Solidified
band, more than 300 authority and 100 prestige. The Act also
wants repressive minority-rights, citizenship, speech and power laws; the
Compact wants liberal ones and a voting franchise. The decision tooltip lists
the accepted laws.

The Mandate System Decision suits a liberal empire in managed decline. It needs
the bar at 65 or more, the Neocolonialism law, a voting franchise, no Outlawed
Dissent and more than 100 authority. It gives a permanent diplomatic-reputation
bonus at a small cost in acceptance, and a year of Positive Colonial
Development.

## How a colonial empire ends

The journal entry ends in one of four ways. The event you get when the empire
holds or collapses depends on the program you ran longest, counting only one
that ran for more than 24 months.

| Ending | Condition | Result |
|---|---|---|
| The empire holds | The bar stays at 100 for 60 consecutive months | Permanent Colonial Empire Solidified, plus a permanent modifier for your path if one program dominated. Overseas states where everyone is well accepted become homelands. After Quiet Assimilation every overseas state of 75,000 people or more does, whatever its acceptance; after The Iron Fist Holds none do, and you gain 25 infamy. You can never get the entry again. |
| Federation | You take the Imperial Federation Act or the Civilizing Mission Compact | Imperial Federation from the decision, plus a permanent The Iron Fist (Act) or The Commonwealth Path (Compact). Well-accepted overseas states become homelands. You can never get the entry again. |
| Collapse | The bar reaches 0 | Up to three of your overseas territories, picked at random, become independent with their homeland regions. Every colonial subject gains Imperial Collapse Aftershock, a large liberty-desire increase for 20 years, and its relations with you drop by 50. The entry can't return for ten years. |
| Voluntary end | You no longer hold any colony or colonial subject while the bar is above 0 | A decaying boost to diplomatic reputation; the event's wording depends on whether you freed colonies by choice. No lockout: new colonies bring the entry back. |

| Longest program | If the empire holds | If it collapses | The countries you free |
|---|---|---|---|
| Military Garrison | The Iron Fist Holds | The Empire Crumbles | Bloody Decolonization Legacy; they start under autocracy with outlawed dissent, and their relations with you fall by 50 |
| Colonial Development Investment | The Commonwealth Path | Negotiated Withdrawal | Commonwealth Legacy; they start as parliamentary republics with protected speech, and relations rise by 30 |
| Cultural Assimilation Programme | Quiet Assimilation | Negotiated Withdrawal | Cultural Assimilation Legacy; they start with Assimilatory Citizenship, and relations rise by 15 |
| none | The Empire Endures | The Empire Crumbles | no legacy |

The legacy applies to the countries you free through the three decisions, and
to those an event frees as a new country. Countries that break away in a
collapse get none of it. On top of the legacy, a Round Table adds 25 to
relations, a single release subtracts 10 and Planned Full Decolonization
subtracts 25. The Empire Crumbles also leaves you with Colonial Empire
Collapsed, a decaying loss of prestige and standard of living; Negotiated
Withdrawal instead gives the same decaying diplomatic-reputation boost as a
voluntary end.

## Decolonization events

Most decolonization events fire for the colonial power while the journal entry
runs. Repressive options usually add Colonial Crackdown, which strengthens your
garrison but costs prestige and bureaucracy and gives the Intelligentsia more
clout; a war fought while it lasts can bring on the Conscription Crisis.
Conciliatory options add Decolonization Negotiations or free the colony. With
the Neocolonialism law, four events offer independence on your terms and give
you Neocolonial Economic Concessions. A colonial subject freed this way leaves
with Neocolonial Dependency, and in The Price of Empire a 25-year treaty also
gives you investment rights and a trade privilege in the new country.

| Event | When it can fire |
|---|---|
| Winds of Change | A colonial subject reaches 50 liberty desire. |
| The World is Watching | An anti-colonial great power presses you over a colonial subject (needs Intergovernmental Organizations). |
| The Price of Empire | A colonial subject at 75 liberty desire rises in armed revolt (needs Civil Rights Movement). |
| Trouble in (the colony's name) | A colony has a severely unaccepted population. |
| Blood in the Colonies | Armed resistance in a colony, once two or more colonies are badly unaccepted. |
| Judged by New Standards | An anti-colonial great power condemns you in international forums. |
| Powerful Friends | A pro-colonial great power offers its backing. |
| These Dark Satanic Mills of Empire, The Intelligentsia Petition | An Anti-Colonialist leads the Intelligentsia. |
| The Treasury Says No | Your debt is high while you hold colonies. |
| Conscription Crisis | You are at war against a rebelling colonial subject or culturally distinct secessionists, or at war while Colonial Crackdown runs. |
| The Universities Speak | The entry has run for ten years and a powerful Intelligentsia is out of government. |
| The Veterans' Protest | Your garrison has run for more than three years. |

### Former colonies

Every colony freed through this system, through an event, or through the base
game's release actions is marked as a former colony of its old ruler. While that
ruler still runs the Colonial Empire entry and is at least a major power, the
former colony may take the initiative. It can propose closer ties (only to an
old ruler with no subjects); if the old ruler accepts in Old Ties, New Terms,
relations improve by 30 and the old ruler gains Post-Colonial Partnership. It
can also demand reparations of a tenth of the old ruler's yearly revenue, capped
at a tenth of its own GDP. In Debts of Empire the old ruler either pays, taking
Colonial Reparations Paid (a ten-year loss of prestige, influence and
bureaucracy) for 40 better relations, or refuses and loses 20.

## How the AI runs its colonies

The AI plays by the same rules and uses the same programs and decisions. An
AI that isn't a great power leans strongly towards Planned Full Decolonization,
more so when three great powers condemn it or three of its colonies are badly
unaccepted. AI great powers are less willing, and no AI plans full
decolonization while two of its colonies are well accepted. In events, AI
empires lean towards negotiation and release, and an AI takes the Imperial
Federation Act or Civilizing Mission Compact whenever it qualifies.

## Turtle Island and the North American Union <!-- style: allow title-case-heading -->

The base game's The Nations of Turtle Island journal entry no longer appears for
the North American Union or United Earth, and a union that already holds it
loses it. This stops the AI switching between Turtle Island and the North
American Union forever. Formable countries are covered in
[Diplomacy](08-diplomacy.md).
