# Social movements

The later eras bring social questions your government must answer: equal rights
for discriminated minorities, human augmentation, digital privacy, mental health
and life after work. Each has a journal entry that opens with a technology and
ends when you settle the question, mostly by passing a law, or when time runs
out. Other movements arrive as events without a journal entry, and religious
revival events push back against secularization. The Social Movements game rule
(on by default) controls the five journal entries and their events; the
movements carried by events run either way.

## Movement journal entries at a glance

All five sit in the journal's Domestic Affairs group, except the Post-Scarcity
Transition (Development). Decentralized countries never get them. The laws are
described in [The mod's new laws](06-politics.md#the-mods-new-laws).

| Journal entry | Appears with | Succeeds when | Fails when | Time limit |
|---|---|---|---|---|
| Civil Rights Movement | Civil Rights Movement (era 7), while an incorporated state holds pops below Provisional Acceptance | Movement Support reaches 100, or you enact Affirmative Action, or Universal Citizenship together with Protection | Movement Support falls to 0, or the Civil Rights political movement is gone | None |
| Human Augmentation Debate | Human Augmentation or Brain-Computer Interfaces (era 11) | Regulated Augmentation Market, Unrestricted Augmentation or Mandatory Augmentation | Human Purity | 20 years |
| Digital Rights & Surveillance | Automated Surveillance or Cybersecurity (era 9) | Strong Privacy Rights | Intrusive Surveillance System and Ministry of Intelligence and Security Established, both at once | 15 years |
| Mental Health Crisis | Mental Health Awareness (era 10) | Rehabilitation-Focused Criminal Justice and the Social Security institution at level 4 or higher | Punishment-Focused Criminal Justice or Penal Labor Camps still in force 10 years after the entry opens | 20 years |
| Post-Scarcity Transition | Universal Basic Income (era 10) | Post-Scarcity Economy law | Never | 30 years |

## The Civil Rights Movement journal entry

The Civil Rights Movement has no timer. A support bar rises or falls, you set
your stance with policy buttons, and how long you held each stance decides which
of ten endings you get.

<!-- screenshot: the Civil Rights Movement journal entry with the Movement Support bar and the policy buttons in view -->

### When the civil rights struggle begins

The entry appears once you have researched Civil Rights Movement and an
incorporated state holds pops with acceptance below Provisional Acceptance
(under 60: Open Prejudice or worse). It becomes active when the Civil Rights
political movement, which the technology brings, has formed. If every such pop
rises to Provisional Acceptance, the entry closes with no outcome and can return
with the grievance. Once it succeeds or fails, it is over for the campaign. A
revolution's winner carries the struggle on, keeping the bar, the policies and
any reward (see [After a revolution](06-politics.md#after-a-revolution)).

### The Movement Support bar

Movement Support starts at 30. At 100 the movement wins; at 0 it collapses. The
bar drifts down on its own, but an ignored movement hovers around 5: only a
crackdown or a Violent Hostility or Ghettoization law can drive it to 0. It
rises with Social Justice Movements (era 9), with Protection or Affirmative
Action in force, with the number of incorporated states holding poorly accepted
pops, with widespread radicals and with the pro-movement policies below. With
Social Justice Movements, Protection and all three pro-movement policies,
support gains about a point a month, so the struggle takes some six years;
without the technology, a decade or more. Enacting Affirmative Action, or
Universal Citizenship with Protection, skips the bar and completes the entry at
once.

As support climbs, the bar's phase adds turmoil penalties and radicals from
political movements, and from 90 it also raises your chance of enacting laws.
The bar's tooltip lists every line. The full list of what moves the bar, with
the phase effects, is in [Appendix: social movement
details](18-appendix-social-movements.md#what-moves-movement-support).

### Civil rights policy buttons

The entry has six policies, each switched on and off with a pair of buttons. The
three pro-movement policies stack, and so do the two crackdowns, but the two
groups exclude each other. Cooptation is limited only by its law requirement.

| Policy | Requires | What it does |
|---|---|---|
| Encourage Grassroots Organizing | No crackdown | Raises support; helps enact laws but brings more radicals |
| Federal Civil Rights Protection | Indifference, Protection or Affirmative Action; Minor Power rank or above; no crackdown | Raises support the most of the three; raises acceptance, costs bureaucracy and authority |
| Gradualist Accommodation | No crackdown | Raises support a little; eases turmoil, raises acceptance slightly |
| Cooptation / Token Reform | Discrimination, Indifference or Cultural Assimilation | Raises support for 12 months only; eases turmoil, costs legitimacy through ideological incoherence |
| Suppression / Crackdown | No pro-movement policy | Lowers support; adds authority and turmoil |
| Segregationist Consolidation | A discriminatory minority law; no pro-movement policy | Lowers support fast; adds authority, but lowers acceptance and brings more radicals |

The discriminatory minority laws are Violent Hostility, Ghettoization, Cultural
Assimilation and Discrimination. Cooptation stops pushing the bar after 12
months in total for the whole struggle; switching it off and on doesn't restart
the count, and its other effects stay. Each button's tooltip lists the modifier
it applies, its monthly push on the bar and the ending its months count toward;
the figures are also in [Civil rights policy
effects](18-appendix-social-movements.md#civil-rights-policy-effects).

### Civil rights events

Four milestone events fire once each, as support first reaches 25, 50, 75 and
90; your minority law and your policies decide which version you get. A random
event also comes about one month in seven. Sympathetic options please the
Intelligentsia, anger the Devout, Rural Folk and Armed Forces, and make
discriminated pops loyal; repressive options do the reverse. The events are
listed in [Civil rights event
list](18-appendix-social-movements.md#civil-rights-event-list).

While you lack Protection, Affirmative Action and Universal Citizenship (or keep
Active Persecution or Legal Guardianship), a great power that has one of those
three and has researched Civil Rights Movement may be asked whether to condemn
you. If it does, you get International Pressure on Human Rights: reject it (−30
relations with the critic), promise reform (+20 relations, a small acceptance
bonus) or counter-accuse (−50 relations and a diplomatic incident). As such a
great power, you get the same question about others.

### How the civil rights struggle ends

The ending depends on how the struggle finished and which policy ran longest; a
policy must run more than 18 months to count. Results decay over ten years.

| Ending | When | Result |
|---|---|---|
| Victory on Paper | Support reached 100 while a discriminatory minority law is in force | Radicals, and either Civil Rights Movement Betrayed (−15% prestige, more turmoil and radicals) or Civil Disobedience Crackdown (+50 Authority, +15% turmoil penalties) |
| The Civil Rights Mandate is Signed | Federal Protection ran longest | +20% prestige, +20 acceptance, −5% Authority |
| The Movement Carries the Day | Grassroots Organizing ran longest | +15% prestige, +15 acceptance, +10% political movement attraction |
| A Settlement, At Last | Gradualist Accommodation ran longest | +10% prestige, +10 acceptance, −5% turmoil penalties |
| Reform on Paper | Cooptation, if no pro-movement policy passed 18 months | +5% prestige, +8 acceptance, more legitimacy penalty from incoherence |
| A New Era of Equality | No pro-movement or cooptation policy passed 18 months | +15% prestige, +15 acceptance, +10 acceptance for cultures sharing no heritage trait with yours |
| The Movement Broken (failure) | You used the crackdowns, or a discriminatory minority law is in force | A choice set by your minority law, from Order Restored to Minority Expulsion Program; all raise Authority and please the Devout, Rural Folk and Armed Forces |
| The Movement Demobilizes (failure) | Cooptation ran over 18 months | Radicals among Academics |
| The Long Drift (failure) | Gradualist Accommodation ran over 18 months | Radicals among lower-strata pops |
| The Movement Fades (failure) | Otherwise | Radicals among lower-strata pops |

Ties between pro-movement policies go to Federal Protection, then Grassroots.

### How the AI handles civil rights

AI countries pick policies mostly by their minority law: Grassroots Organizing
under Indifference or better, Federal Protection under Protection or Affirmative
Action, Cooptation under Discrimination, the crackdowns under Violent Hostility
or Ghettoization, and Gradualist Accommodation anywhere. The Intelligentsia in
government also draw them to Grassroots Organizing, and the Landowners to
Suppression / Crackdown. They never switch a policy off.

## Debates settled by law

The other four journal entries share a simpler shape. Each applies a modifier
while it runs and has up to a one-in-five chance each month of one of its five
events, whose options run from paying for reform to a hard-line response. It
ends when you enact the settling law, or times out with radicals and a penalty.
Outcome modifiers decay over ten years.

| Journal entry | While active | Success | Failure | Time-out |
|---|---|---|---|---|
| Human Augmentation Debate | +5% innovation, +5% turmoil penalties | +10% innovation, +5% prestige | −10% innovation and −2% prestige, or +15% turmoil penalties and −5% prestige (your choice) | +15% turmoil penalties |
| Digital Rights & Surveillance | +50 Authority, +5% turmoil penalties | +5% prestige, +5% innovation | +150 Authority, −5% innovation, −5% prestige; or radicals | −25 prestige, +5% turmoil penalties |
| Mental Health Crisis | +3% mortality | −3% mortality, +5% prestige | +5% mortality, −5% prestige; or radicals | +5% mortality, −25 prestige |
| Post-Scarcity Transition | +10% turmoil penalties | +15% prestige, +10% innovation | Can't fail | +15% turmoil penalties, −50 prestige |

### The augmentation debate

Every country starts on No Augmentation, and staying on it or Medical
Augmentation Only runs the clock out. Regulated Augmentation Market needs Human
Augmentation and the Ministry of Consumer Protection Established law,
Unrestricted Augmentation needs Brain-Computer Interfaces, and Mandatory
Augmentation needs Bioenhanced Soldiers and the Ministry of War Established law.
The events cover a society divided by augmentation, black-market implants,
workplace discrimination, augmented crime and religious condemnation.

### The digital rights debate

The entry opens in era 9, but Strong Privacy Rights needs Universal Digital
Identity from era 11 and the Guaranteed Liberties law, and you have 15 years.
The events bring a whistleblower, a data breach, hackers, predictive policing
and foreign cyber-espionage; with Covert Warfare on, the last follows only when
your counterintelligence catches a foreign espionage operation (see [What the
target learns](11-influence.md#what-the-target-learns)).

### The mental health debate

Rehabilitation-Focused Criminal Justice unlocks with the technology that opens
the crisis, so raising Social Security to level 4 is usually the slow half.
You have ten years to move off Punishment-Focused Criminal Justice, the law
every country starts with. If it is still in force when the decade ends, the
crisis fails, and Penal Labor Camps fails it the same way. Reforming in time
leaves the other ten years to raise Social Security. The events deal with burnout, youth mental health, addiction, veterans'
PTSD and a care-home scandal.

### The post-scarcity debate

This entry can't fail: it succeeds or times out. It opens in era 10, while the
Post-Scarcity Economy law needs the era 12 technology of that name, so the 30
years are a race through two eras (see [The extended timeline](02-timeline.md)).
The events bring unemployment protests, a crisis of meaning, AI replacing
bureaucrats, neo-Luddite terrorism and an art renaissance.

## Movements carried by events

Second-wave feminism, LGBTQ+ rights, secularization and environmentalism have no
journal entry. They come as random events once you have the technology, and the
Social Movements rule doesn't stop them.

| Movement | Needs | Events |
|---|---|---|
| Second-wave feminism | Second Wave Feminism (era 7) | The Second Shift and Half the Salary, once each, over women's work and equal pay |
| LGBTQ+ rights | LGBTQ+ Rights Movement (era 9) | Pride and Protest, at most once in ten years until you enact Full Equality and Protection; The Marriage Equality Question, once, under Basic Protections or Anti-Discrimination Laws |
| Secularization | One of several technologies, such as Sexual Revolution or Social Media, or the Total Separation law | Religious Revival Sweeps the Nation and Faith Against Modernity, each at most once in ten years and never under State Atheism |
| Environmentalism | The Global Warming journal entry | Climate events as world temperature crosses thresholds, under the Global Warming rule; see [Climate and pollution](15-climate.md) |

Their options are in [Details of the movements carried by
events](18-appendix-social-movements.md#details-of-the-movements-carried-by-events).

The Anti-War and Transhumanist political movements also bring events of their
own, described with the movements in [New political
movements](06-politics.md#new-political-movements).

## Religious revival events

Seven religious revival events push back against the Devout interest group's
decline. Each is tied to a technology of eras 7 to 9 and fires at most once per
campaign, at least five years apart. They need a Devout group that is weak but
present (clout above 2% and below 10%, or 15% for three of them), a church law
other than State Religion or its Millet System and People of the Book variants,
and neither Autocracy nor Oligarchy. State Atheism blocks all but two of them.

Each event offers three choices. Embracing the revival grants a modifier for 20
years that raises Devout political strength and attraction, some with a side
effect such as lost Authority or a little standard of living. A moderate choice
gives a weaker modifier that fades over 20 years, and a secular choice
radicalizes Devout pops. The embrace modifiers stack, so taking several can make
the Devout a leading interest group again. AI countries embrace more readily
with a powerful Devout group or a Ministry of Religion. The seven events and
their modifiers are in [Religious revival event
list](18-appendix-social-movements.md#religious-revival-event-list).

<!-- screenshot: a religious revival event, such as The Moral Majority, with its three options -->

Once you have Decline of Organized Religion and any embrace modifier, the
Secularization Campaign decision appears. It removes all seven embrace modifiers
at once, radicalizes Devout pops, and leaves the moderate modifiers in place.

## What the Social Movements rule turns off

With Social Movements Disabled, none of the five journal entries opens, so their
buttons, events and endings never happen. The technologies and laws stay, the
Civil Rights political movement still forms with its technology, and the
feminism, LGBTQ+, faith, religious revival and political-movement events still
fire. Environmental events follow the Global Warming rule.
