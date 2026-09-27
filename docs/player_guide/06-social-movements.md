# Social movements

The later eras bring social questions your government must answer: equal
rights for discriminated minorities, human augmentation, digital privacy, mental
health and life after work. Each has a journal entry that opens with a
technology and ends when you settle the question, mostly by passing a law, or
when time runs out. Other movements arrive as
events without a journal entry, and religious revival events push back against
secularization. The Social Movements game rule (on by default) controls the five
journal entries; the event chains run either way.

## Movement journal entries at a glance

All five sit in the journal's Domestic Affairs group, except the Post-Scarcity
Transition (Development). Decentralized countries never get them. The laws are described in
[Government, laws and characters](05-politics.md).

| Journal entry | Appears with | Succeeds when | Fails when | Time limit |
|---|---|---|---|---|
| Civil Rights Movement | Civil Rights Movement (era 7), while an incorporated state holds pops below Provisional Acceptance | Movement Support reaches 100, or you enact Affirmative Action, or Universal Citizenship together with Protection | Movement Support falls to 0, or the Civil Rights political movement is gone | None |
| Human Augmentation Debate | Human Augmentation or Brain-Computer Interfaces (era 11) | Regulated Augmentation Market, Unrestricted Augmentation or Mandatory Augmentation | Human Purity | 20 years |
| Digital Rights & Surveillance | Automated Surveillance or Cybersecurity (era 9) | Strong Privacy Rights | Intrusive Surveillance System and Ministry of Intelligence and Security Established, both at once | 15 years |
| Mental Health Crisis | Mental Health Awareness (era 10) | Rehabilitation-Focused Criminal Justice and the Social Security institution at level 4 or higher | Punishment-Focused Criminal Justice once you have researched Decline of Organized Religion | 20 years |
| Post-Scarcity Transition | Universal Basic Income (era 10) | Post-Scarcity Economy law | Never | 30 years |

## The Civil Rights Movement journal entry

The Civil Rights Movement has no timer. A support bar rises or falls, you set
your stance with policy buttons, and how long you held each stance decides which
of ten endings you get.

<!-- screenshot: the Civil Rights Movement journal entry with the Movement Support bar and the policy buttons in view -->

### When the civil rights struggle begins

The entry appears once you have researched Civil Rights Movement and an
incorporated state holds pops with acceptance below Provisional Acceptance (under
60: Open Prejudice or worse). It becomes active when the Civil Rights political
movement, which the technology brings, has formed. If every such pop rises to Provisional Acceptance, the entry
closes with no outcome and can return with the grievance. Once it succeeds or
fails, it is over for the campaign. A revolution's winner carries the struggle
on, keeping the bar, the policies and any reward (see
[Government, laws and characters](05-politics.md)).

### The Movement Support bar

Movement Support starts at 30. At 100 the movement wins; at 0 it collapses. Each
month it moves by the sum of these lines, which the bar's tooltip lists:

| Source | Change per month |
|---|---|
| Movement decay (always) | −0.4 |
| Social Justice Movements researched (era 9) | +0.4 |
| Protection or Affirmative Action in force | +0.3 |
| Violent Hostility or Ghettoization in force | −0.5 |
| Incorporated states with pops below Provisional Acceptance | Up to +0.5 (at 40 states) |
| Radicals at 10% of your population, and again at 20% | +0.15 each |
| Encourage Grassroots Organizing | +0.2 |
| Federal Civil Rights Protection | +0.3 |
| Gradualist Accommodation | +0.1 |
| Cooptation / Token Reform (first 12 months) | +0.15 |
| Suppression / Crackdown | −0.6 |
| Segregationist Consolidation | −0.9 |
| Support below 5 | +0.4 |

The last line cancels the decay near the bottom, so an ignored movement hovers
around 5; only a crackdown or a Violent Hostility or Ghettoization law can drive it
to 0. With Social Justice Movements, Protection and all three pro-movement
policies, support gains about a point a month, so the struggle takes some six
years; without the technology, a decade or more. Enacting Affirmative Action,
or Universal Citizenship with Protection, skips the bar and completes the entry
at once.

### Civil rights phases

The bar's level sets a phase, applied as a modifier on the journal entry:

| Phase | Support | Effects |
|---|---|---|
| Marginal | Below 20 | −10% radicals from political movements |
| Growing | 20–40 | +5% turmoil penalties |
| Active | 40–65 | +5% turmoil penalties, +10% radicals from political movements |
| Pressuring | 65–90 | +10% turmoil penalties, +20% radicals from political movements |
| Imminent Reform | 90 and above | +15% turmoil penalties, +20% radicals from political movements, +10% enactment success chance |

### Civil rights policy buttons

The entry has six policies, each switched on and off with a pair of buttons. The
three pro-movement policies stack, and so do the two crackdowns, but the two
groups exclude each other. Cooptation is limited only by its law requirement.

| Policy | Requires | Support per month | While active |
|---|---|---|---|
| Encourage Grassroots Organizing | No crackdown | +0.2 | +5% enactment success chance, +10% radicals from political movements |
| Federal Civil Rights Protection | Indifference, Protection or Affirmative Action; Minor Power rank or above; no crackdown | +0.3 | +5 acceptance, −5% Bureaucracy, −5% Authority |
| Gradualist Accommodation | No crackdown | +0.1 | −5% turmoil penalties, +2 acceptance |
| Cooptation / Token Reform | Discrimination, Indifference or Cultural Assimilation | +0.15 for 12 months | −10% turmoil penalties, +3 acceptance, +5% legitimacy penalty from ideological incoherence |
| Suppression / Crackdown | No pro-movement policy | −0.6 | +5% Authority, +10% turmoil penalties |
| Segregationist Consolidation | A discriminatory minority law; no pro-movement policy | −0.9 | +10% Authority, +30% radicals from political movements, −10 acceptance |

Acceptance figures apply to pops outside their homeland. The discriminatory
minority laws are Violent Hostility, Ghettoization, Cultural Assimilation and
Discrimination. Cooptation stops pushing the bar after 12 months in total;
switching it off and on doesn't restart the count, whatever the button's
description says, and its other effects stay.

### Civil rights events

Four milestones each bring one event, once, when the bar first crosses their
mark:

| Support reaches | Event | Instead, when |
|---|---|---|
| 25 | First Mass Rally Draws Notice | The Underground Railroad, under Violent Hostility or Ghettoization |
| 50 | Coalition Forms with Trade Unions | Blood of a Martyr, under a discriminatory minority law |
| 75 | Mass Disobedience, only under a discriminatory minority law (otherwise no event) | Federal Commission Recommends Action, if Federal Protection has run over 24 months |
| 90 | The March on the Capital | Always this one |

In about one month in seven, a random event may also come: Civil Rights March,
Segregation Incident (under a discriminatory minority law), Cultural
Renaissance (at 40% literacy), The Boycott, or the international condemnation
described below. Sympathetic options please the Intelligentsia, anger the
Devout, Rural Folk and Armed Forces, and make discriminated pops loyal;
repressive options do the reverse.

While you lack Protection, Affirmative Action and Universal Citizenship (or keep
Active Persecution or Legal Guardianship), a great power that has one of those
three and has researched Civil Rights Movement may be asked whether to condemn
you. If it does, you get International
Pressure on Human Rights: reject it (−30 relations with the critic), promise
reform (+20 relations, a small acceptance bonus) or counter-accuse (−50
relations and a diplomatic incident). As such a great power, you get the same
question about others.

### How the civil rights struggle ends

The ending depends on how the struggle finished and which policy ran longest;
a policy must run more than 18 months to count. Results decay over ten years.

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
under Indifference or better, Federal Protection under Protection or
Affirmative Action, Cooptation under Discrimination, the crackdowns under
Violent Hostility or Ghettoization, and Gradualist Accommodation anywhere. The
Intelligentsia in government also draw them to Grassroots Organizing, and the
Landowners to Suppression / Crackdown. They never switch a policy off.

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
Identity from era 11 and the Guaranteed Liberties law, and you have 15 years. The events bring a whistleblower, a
data breach, hackers, predictive policing and foreign cyber-espionage; with
Covert Warfare on, the last follows only when your counterintelligence catches a
foreign espionage operation (see
[Cultural hegemony and covert warfare](10-influence.md)).

### The mental health debate

Rehabilitation-Focused Criminal Justice unlocks with the technology that opens
the crisis, so raising Social Security to level 4 is usually the slow half.
Researching Decline of Organized Religion while Punishment-Focused Criminal
Justice is in force fails the crisis on the spot. The events deal with burnout,
youth mental health, addiction, veterans' PTSD and a care-home scandal.

### The post-scarcity debate

This entry can't fail: it succeeds or times out. It opens in era 10, while the Post-Scarcity
Economy law needs the era 12 technology of that name, so the 30 years are a race
through two eras (see [The extended timeline](02-timeline.md)). The events bring
unemployment protests, a crisis of meaning, AI replacing bureaucrats,
neo-Luddite terrorism and an art renaissance.

## Movements carried by events

Second-wave feminism, LGBTQ+ rights, secularization and environmentalism have no
journal entry, though the Social Movements rule's description still lists all
four as journal entries. They come as random events once you have the
technology, and the rule doesn't stop them. The Anti-War and Transhumanist
political movements also bring events of their own; see
[Government, laws and characters](05-politics.md).

### Second-wave feminism events

Two events need Second Wave Feminism (era 7), and each fires once. The Second
Shift, under Propertied Women or Women in the Workplace, trades research speed
against legitimacy: welcoming women into the workforce angers aristocrats,
keeping traditional roles slows research. Half the Salary, under Women in the
Workplace, asks for equal pay: passing it pleases the Intelligentsia and angers
the Devout, Rural Folk and Armed Forces, and shelving it does the reverse.

### LGBTQ+ rights events

These need LGBTQ+ Rights Movement (era 9). Pride and Protest can recur, at most
once in ten years, until you enact Full Equality and Protection; its options, from protecting
the march to breaking it up, depend on your LGBTQ+ Rights law. The Marriage
Equality Question fires once, under Basic Protections or Anti-Discrimination
Laws, offering civil partnerships, marriage equality, a traditional definition
or waiting for the courts.

### Secularization and faith events

Two events carry the conflict between faith and modern life. Both are in the
yearly draw of social-tension events, which has a 65% chance each year of
picking one event from a large pool. Neither fires under State Atheism, and
each comes at most once in ten years. Religious Revival Sweeps the Nation needs a marginalized
Devout group and Decline of Organized Religion (era 10), Sexual Revolution or
Social Media: you
embrace it (Devout political strength up, Authority down), stay secular (a small
research bonus) or channel it into charity (a little standard of living). Faith
Against Modernity needs Devout clout of at least 5% and a progressive law or
technology:
you side with tradition, modernize, or seek a theological compromise.

### Environmentalism belongs to climate

Environmental events belong to the Global Warming journal entry and its game
rule, and fire as world temperature crosses thresholds. See
[Climate and pollution](14-climate.md).

## Religious revival events

Seven religious revival events push back against the Devout interest group's
decline. Each is tied to a technology and fires at most once per campaign, at
least five years apart. They need Devout clout above 2% and below 10% (15% for
One Nation Under God, The Culture War and The Faithful Hand), a church law other
than State Religion or its Millet System and People of the Book variants, and
neither Autocracy nor Oligarchy. State Atheism blocks
all but The Preferential Option and The Faithful Hand, which then
tell of underground faith.

| Event | Technology (era) | Embracing it grants, for 20 years |
|---|---|---|
| The Moral Majority | Television Broadcasting (7) | The Religious Right: +35% Devout political strength, +30% Devout attraction, −50 Authority |
| The Electronic Pulpit | Pop Culture (7) | Televangelism Movement: +20% strength, +50% attraction |
| The Preferential Option | Civil Rights Movement (7) | Liberation Theology: +30% strength, +25% attraction, +0.5 standard of living |
| One Nation Under God | Globalization (9) | Religious Nationalism: +50% strength, +40% attraction, +10% assimilation, −5% prestige (fading) |
| The Digital Pulpit | Social Media (9) | Digital Faith Movement: +25% strength, +45% attraction |
| The Culture War | Sexual Revolution (8) | Culture War: +40% strength, +35% attraction, slower research (fading) |
| The Faithful Hand | Social Justice Movements (9) | Faith-Based Social Services: +25% strength, +30% attraction, +0.5 standard of living (fading) |

Each event also offers a moderate choice with a weaker modifier that fades over
20 years, and a secular choice that radicalizes Devout pops. The embrace
modifiers stack, so taking several can make the Devout a leading interest group
again. AI countries embrace more readily with a powerful Devout group or a
Ministry of Religion.

<!-- screenshot: a religious revival event, such as The Moral Majority, with its three options -->

Islamic and Dharmic countries get their own text for all seven events, and some
titles change: The Electronic Pulpit becomes The Satellite Minbar for Islamic
countries, and One Nation Under God becomes One Ummah, One Law; One
Civilization, One Dharma; or, for Jewish countries, The Promised Land.

Once you have Decline of Organized Religion and any embrace modifier, the
Secularization Campaign decision appears. It removes all seven embrace
modifiers at once, radicalizes Devout pops, and leaves the moderate modifiers
in place.

## What the Social Movements rule turns off

With Social Movements Disabled, none of the five journal entries opens, so their
buttons, events and endings never happen. The technologies and laws stay, the
Civil Rights political movement still forms with its technology, and the
feminism, LGBTQ+, faith, religious revival and political-movement events still
fire. Environmental events follow the Global Warming rule.
