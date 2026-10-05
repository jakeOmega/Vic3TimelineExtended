# Taxation (experimental)

Under the Legislated Tax Code game rule, taxation stops being a taxation law plus
a tax level. Each country has one tax code instead: a set of rates written into
law. You change it by drafting a reform, introducing it as a bill, winning enough
interest groups over and choosing the month it takes effect. The rule is
experimental and off by default. It has three settings: *Tax Code Disabled* keeps
base-game taxes, *Tax Code Enabled* legislates domestic taxes, and *Tax Code and
Customs Enabled* also legislates tariffs and subsidies (see the
[Introduction](01-introduction.md)). Choose it when you set up the campaign; it
can't be switched later.

Everything happens in the Tax Code journal entry, in the Domestic Affairs group,
and in the Budget panel's Tax Code tab. Both show the same panels. AI countries
legislate through the same bills and the same rules (see
[How AI countries legislate taxes](#how-ai-countries-legislate-taxes)).

## The Legislated Tax Code game rule

At the start of the game each country's taxation law and tax level are carried
over into its code, rate for rate. A country that was taxing grain keeps grain
on its list of taxed goods. The code starts out collecting what the base game
would have collected. Decentralized countries have no tax code.

### What the tax code replaces

The five taxation laws, from Consumption-Based Taxation to Graduated Taxation,
can't be enacted under the rule. Every country holds the Legislated Tax Code law
in the Taxation group instead, and each rate is an amendment to it, such as Wage
Tax 10%. The Taxation Level stays at Medium, because the code's rates are the
whole tax. The base-game controls that would change a rate are grayed out: the
tax level buttons, the add-consumption-tax menu, and the Tax and Untax toggles
in the goods panel and the goods right-click menus. Under *Tax Code and Customs
Enabled* the tariff and subsidy buttons are grayed too.

On the 1st of every month the code puts its rates, taxed goods and relief back
in place. A change made any other way, by an event or by an AI country's own
tax decisions, lasts at most until then.

No interest group takes a stance on the Legislated Tax Code law itself. Each
group judges your code as the taxation law it comes closest to:

| The code counts as | When it |
|---|---|
| Graduated Taxation | taxes wages at 10% or more and dividends at least as heavily |
| Proportional Taxation | taxes wages at 10% or more and dividends at all |
| Per-Capita Taxation | levies a wage tax and a head tax |
| Land-Based Taxation | levies a rural assessment |
| Consumption-Based Taxation | does none of the above |

A group's approval then counts as it would for that law, and its approval
breakdown says so: Endorses the Tax Code, Strongly Opposes the Tax Code and so
on. The judgement is renewed on the 1st of every month. The same mapping decides
three base-game journal entries that ask for a taxation law: Great Reforms:
Bureaucratic Reform, Imperialism of Promise and Our Fortunate Regeneration
complete when your code counts as the law they ask for.

Two things don't carry over. The Consumption-Based Taxation law's bureaucracy and
authority discounts go with the law. The base game's Short-Term Tax Cuts amendment
can't be added under the rule; a bill with an expiry date replaces it. The
religious tax of the Millet System and People of the Book and the land tax of
State Redemption Payments stay outside the code, collected at the Medium level.

### Taxes the code sets

| Provision | Steps and range | Who pays | Budget line |
|---|---|---|---|
| Wage Tax | 2.5% steps, 0% to 50% | pops on their wages | Income Taxes |
| Dividend Tax | 2.5% steps, 0% to 50% | pops who own private buildings, on their dividends | Dividends Taxes |
| Rural Assessment | steps of 0.025, up to 1.2 | peasants and farmers in agricultural buildings, who then pay no head tax | Land Taxes, part of Poll Taxes |
| Head Tax | steps of 0.05, up to 1.5 | working adults who pay no rural assessment | Per Capita Taxes, part of Poll Taxes |
| Consumption Tax | 5% steps, 0% to 60% | pops buying a good on the taxed goods list | Consumption Taxes |
| Taxed Goods | any good pops buy, on or off | as Consumption Tax | Consumption Taxes |
| Agricultural Relief | 25% or 50% | halves (or cuts by a quarter) the wage tax of workers in agricultural buildings | Income Taxes |
| Regional Relief | 25% or 50% | every tax collected from pops in up to three named states | every line |

Rural Assessment and Head Tax are flat amounts, shown with a money icon. The
Consumption Tax rate applies to every good on the list, so the list decides
what a consumption tax collects and the rate decides how much. Under *Tax Code
and Customs Enabled* the code also holds an import and an export level for
every tradeable good (see [Customs under the tax code](#customs-under-the-tax-code)).

## The Tax Code tab

The Tax Code tab sits beside the base game's Budget tabs. It opens once your
taxes are under the code, at the start of the game, and its tooltip lists what
is missing while it is grayed. The journal entry has the same panels and an
Open Budget button.

<!-- screenshot: the Budget panel's Tax Code tab, overview and Enacted Code open -->

The overview gives your code's version and its Last Change and Next Change,
the bill under debate and the open Draft Reform, your Promises, and the date of
the Economy Snapshot the estimates use. Below it:

- Enacted Code lists every rate in force, when it came into force and, for a
  temporary rate, when it expires and what replaces it.
- History lists the last eight changes: bills passed and taking effect, rates
  expiring, promises kept or broken, held bills.
- How Tax Legislation Works, collapsed by default, repeats the rules of this
  chapter with the exact figures your game uses.

## Drafting a tax reform

A reform starts as a draft, and a draft changes nothing. Draft a Reform opens
one. If a bill is already under debate the button reads Draft a Revision, and
the draft starts from that bill.

### The draft reform workbench

The Draft Reform section groups the provisions under Income, Land and Head,
Consumption, Relief and Commencement, with a Goods Catalog for the taxed goods.
Each row shows three columns:

| Column | Shows |
|---|---|
| Law | the rate existing law will have in the draft's commencement month: today's rate, unless a temporary rate expires or a passed bill takes effect before then |
| Draft | the rate the draft sets |
| Change | the difference |

Click − or + to move a rate one step, shift-click to set it to zero or its
highest rate, and right-click to take it out of the draft, leaving it as
existing law has it. In the Goods Catalog, Tax and Exempt change a good and
Undo takes it out of the draft. Discard closes the draft.

If a passed bill, or a change made outside legislation, alters a tax after you
changed it in the draft, the draft's row is marked Changed Since Drafted. Accept
the new baseline before you introduce the draft; your own value stays.

### Commencement and temporary tax rates

Takes Effect sets the month the reform comes into force, on the 1st. It can be
next month or up to 60 months ahead, and starts three months ahead. The bill must
pass before that month comes.

Each changed rate can be Permanent or expire after 6, 12, 24, 36 or 60 months.
When it expires, the rate beneath it returns: the rate that was law before this
bill, or the rate an earlier temporary change was due to return to. A later bill
that changes the same tax replaces the expiry. A permanent change clears it, and
a temporary one keeps the rate that was due to return. A temporary rise is how
you pay for a war without raising taxes for good.

### Agricultural and regional tax relief

Both kinds of relief move in bands of 25%, up to 50%.

Agricultural relief cuts the wage tax of workers in agricultural buildings. It
is worth nothing to interest groups while you levy no wage tax.

Regional relief reduces every tax collected from pops in up to three of your
incorporated states. Choose States lists them, with each state's population and
the taxes it pays a week. Name adds a state and Drop removes one. A named state
shows Regional Tax Relief 25% or 50% among its modifiers. A state you lose drops
out of the relief.

### Reviewing a tax draft

Review opens the comparison of your draft with existing law. Each changed tax
shows Existing Law and With This Bill, with the expiry and what returns after
it, and a revenue estimate (see [Revenue estimates](#revenue-estimates)). The
review also lists the passed bills waiting to take effect and any customs
changes.

Bill Class says whether the bill is minor or major. A minor bill moves at most
two taxes by at most two steps each, and touches no goods, relief or customs.
It needs 15 days of debate instead of 30.

## Passing a tax bill

Introduce makes your draft a bill and opens debate. The draft stays open, so
you can work on a revision while the bill is debated.

### Conditions for passage

The Bill Under Debate section lists the Conditions for Passage. Pass is
available once all of them hold:

| Condition | Requirement |
|---|---|
| Committed Clout | committed groups hold more than 50% of the clout of all groups that aren't marginal |
| Legitimacy | at least 25 |
| Debate | 30 days since the last revision, 15 for a minor bill |
| Takes Effect | the commencement month is still ahead |
| Waiting Bills | fewer than two passed bills waiting to take effect |
| Outside Changes | nothing outside legislation has changed a tax the bill changes since you introduced it |

<!-- screenshot: the Bill Under Debate section with the committed-clout bar and interest group cards -->

When a bill passes, each group that opposed it and did not commit disapproves
of the government: −3 approval, fading over 180 days. If the commencement month
arrives while the bill is still in debate, Move to Next Month moves it a month
later without losing its commitments.

### How interest groups judge a tax bill

Each interest group gets a card with a score from −100 to +100, made of:

| Reason | What it counts |
|---|---|
| Cost to Members | the taxes, taxed goods and relief the bill changes, weighted by what the group's members pay |
| Views on Taxation | whether the bill makes the code more progressive (wage and dividend taxes) or more regressive (rural assessment, head and consumption taxes, taxed staples), against the group's views of the taxation laws |
| State of the Budget | with a deficit on the 1st of the month, a bill that raises revenue scores better; with a surplus, one that cuts taxes does |
| In Government | +10 for a group in government |
| Promises | promises made to the group under this bill |
| Kept Promises | the group's record of your earlier promises |

A group scoring 20 or more is Committed: it commits to the bill's current
revision and stays committed whatever happens to its score. A group at −40 or
below draws a Red Line. Between the two a group is Persuadable if its score is
0 or more and Opposed below that. A Marginal group counts for nothing until it
grows, but it can still hold a commitment that counts once it does. The cards
are refreshed on the 1st of every month and whenever the bill changes.

### Offers from interest groups

A group that has not committed may make one offer per revision:

- Soften the rise it minds most by one step, never below existing law.
- Add a band of agricultural relief.
- Leave a staple it would pay for untaxed.
- A promise (see [Promises to interest groups](#promises-to-interest-groups)).

A group at its red line offers only promises. The card shows what the group
asks for, what accepting gives, and for a tax change the revenue you give up.
Accept carries the offer out. Any acceptance makes a new revision, so debate
starts again and every other group reconsiders. A group that was Persuadable
when you accepted commits at once. An Opposed or Red Line group only opposes
the bill less, and commits only if its new score reaches 20.

| Offer | You give up | Worth it when |
|---|---|---|
| Soften a rise | part of the revenue the bill raises | the group's clout carries the bill over 50% and the rest of the rise still meets your need |
| Agricultural relief | wage tax from farm workers | Rural Folk or Landowners hold the clout you need and few of your wage earners farm |
| Leave a staple untaxed | that good's consumption tax | the bill raises other taxes enough without it |
| A promise | nothing now; an obligation for years | you can deliver it, see below |

A group never gains the same change twice in one bill, and no group can be
promised what is already pending or in force.

### Revising, withdrawing and forcing a tax bill

To change a bill under debate, open Draft a Revision, edit it, and click Revise
Bill or Revise from Draft. A revision releases every commitment, withdraws every
offer and restarts the debate. Promises you accepted under the bill stay on the
new revision; a revision from the draft drops them. Withdraw closes the bill and
leaves the code as it was. Introducing and withdrawing a bill costs nothing.

Force Through passes a bill that is short of a majority. It needs Legislative
Override Capacity of at least 2, committed groups holding at least 35% of the
clout, enough authority to pay for it, and every other condition for passage.
It costs authority and 5
legitimacy, angers the opposition and spends override capacity, as forcing a
law through does, with the effects fading over five years.

## Promises to interest groups

A promise is something the government undertakes in return for a group's
commitment. It does nothing by itself: it records what you must bring about,
and the game checks on the 1st of every month whether you did. You can have at
most four promises at once.

| Promise | Deliver within | Then keep for |
|---|---|---|
| Ministry of Education or Ministry of Health one level higher | 12 months per level to gain, plus 6 | 24 months |
| No bureaucracy deficit | 12 months | 24 months |
| Fixed income above fixed expenses, six months running | 24 months | 12 months |

A promise starts as Pending: it binds only if the revision it was made under
passes, and a revision or a withdrawn bill releases it. Once the bill passes it
binds when the bill takes effect, and its clock starts then. A promise of
something you already have reads Maintain instead of Reach; it wins less
support and earns no trust when kept.

The institution counted is the level reached, not the level it is growing to. A
bureaucracy deficit never breaks an institution promise: each month of deficit
moves its deadline a month later, since the institution can't grow meanwhile.
During its term an institution level must hold every month. A bureaucracy or
budget promise breaks only after three failing months in a row; the budget and
the bureaucracy count as they stood on the 1st.

| Outcome | Group's approval | Trust |
|---|---|---|
| Kept Tax Promise | +3 | +1, not for a promise that only maintained |
| Broken Tax Promise | −5 | −1 |
| Renegotiated Tax Promise | −2 | −1 |

Each reaction fades over 180 days. Renegotiate ends a promise that is in force
before it breaks. Trust shows on the group's card as Kept Promises, 10 points per
step, and fades a step back toward neutral after 24 months without a kept,
broken or renegotiated promise. Breaking a promise never repeals a tax bill.

Promise what you were going to do anyway. A ministry you planned to expand, or
a deficit your new taxes will close, buys commitment for nothing extra.

## Passed tax bills

A passed bill waits in Passed Bills until its month, then takes effect on the
1st, all at once. Collections change then, not before. If another sync of the
code already ran that day, the new rates start collecting on the 2nd.

### When passed bills overlap

At most two passed bills can wait at once. A bill passed later that takes effect
no later than an earlier one replaces whatever the two change in common. A bill
passed later that takes effect after it simply follows it.

### Held tax bills

A passed bill is held back, whole and changing nothing, in two cases:

- A change made outside legislation reached a provision it changes before it
  took effect. Such a bill can only be dropped; Drop frees its slot.
- Its month went by before it could take effect. If it is at most three months
  late and no later bill has changed what it changes, Move to Next Month puts
  it back on the calendar. Otherwise it can only be dropped.

Promises bound to a dropped bill lapse without penalty.

## Revenue estimates

The review and the offers show a Revenue Estimate for each Budget line a change
touches: Income Taxes, Dividends Taxes, Poll Taxes and Consumption Taxes. It
scales the line's current weekly receipts by the change in rate, against the
Economy Snapshot taken on the 1st of the month. It is a static estimate: pops,
wages, prices and purchases as they are now. Poll Taxes shows a range when both
the rural assessment and the head tax collect, because today's receipts don't
say how they divide.

A tax you don't collect now has no current base, and its line says so. Taxed
goods, agricultural relief and customs get no figure. Regional relief shows its
estimate on each named state. An estimate whose snapshot is older than the
code or the bill it describes is marked out of date.

## Customs under the tax code

Under *Tax Code and Customs Enabled* the code also holds an import and an
export level for every tradeable good, from Max subsidy through None to Max
tariff, and a bill changes them like any tax. The workbench's Customs section
lists the goods as Staples, Industrial Goods, Luxuries and Military Goods;
click a step, or right-click to take a level out of the draft. A customs change
always makes a bill major.

Only the country that owns a market sets its levels. A country trading in
another country's market sees them as set by that market's owner, and its bills
can't change them. A country that comes to own its market takes the market's
levels into its code the next month.

On the 1st of every month the code sets each level back. A level that doesn't
take, because a treaty forbids it or the tariff cooldown refuses it, is tried
again every month. After four months in a row the code adopts the market's
level instead, and the review marks the good as blocked. Losing your market
keeps your levels on record, drops the customs changes from your draft and bill
(withdrawing a bill that changed nothing else), and holds back a passed bill
that changes customs.

Interest groups weigh customs like taxes: an import tariff on staples pleases
Rural Folk and Landowners and costs Trade Unions, one on industrial goods
pleases Industrialists, and subsidies work the other way.

## The tax code in revolutions and new countries

When a revolution breaks out, both sides keep the code, the passed bills with
their dates and the promises in force. Each side collects from its own
territory and can pass its own bills. When the war ends, the winner's code,
including its wartime bills, applies across the reunited country; History shows
The tax code was restored after a civil war. Bills in debate and open drafts
are closed. Promises whose bill no longer waits, or whose group no longer
exists, lapse without penalty (see also
[After a revolution](06-politics.md#after-a-revolution)).

A country released from yours starts with your enacted code, without your
bills or promises. A country released from one without a code, and a country
formed by unification, carries over its own taxation law as it would at the
start of the game.

## How AI countries legislate taxes

AI countries draft, introduce and pass bills through the same conditions as
you. They get no taxes for free, and no bill passes for them without the
committed clout, legitimacy and debate it needs.

An AI country counts deficits and surpluses from its budget on the 1st of each
month, and reads its income, debt and gold reserves when it acts:

- After three months of fixed deficit, with income at most 90% of expenses
  (110% if it has significant debt) and its gold reserves under a tenth of
  their limit, it introduces a bill raising one or two taxes by a step. It
  picks the taxes its interest groups mind least. When raising the consumption
  rate is the cheapest choice and it taxes fewer than four goods, it taxes up
  to two luxury goods instead.
- At war it prefers a two-step rise of a single tax that expires after 24
  months.
- After six months of surplus, with income at least 125% of expenses (150% if
  it has significant debt) and its gold reserves at least a tenth of their
  limit, it cuts the tax its groups mind most by a step.
- In a financial emergency (default, heavy debt, or bankruptcy within about
  30 weeks) it introduces a minor bill at once, with 15 days of debate, and
  forces it through if enough groups back it and it has the override capacity
  and the authority. After an emergency bill passes it waits about three
  months before the next, so the first can show in its budget; after one fails
  it waits six.

It looks at new bills about once every three months, and waits a year after a
bill takes effect before starting another. It accepts interest-group offers
until the bill can pass, and accepts a promise only when it can keep it. When
it is about to miss a Ministry of Education or Ministry of Health promise it
raises the institution itself. It renegotiates a bureaucracy or budget promise
rather than break it. A bill that can't pass is withdrawn, and the country
waits six months before trying again. Held bills are moved or dropped.

Under *Tax Code and Customs Enabled* AI countries pass no customs bills yet.
Their tariffs follow the base game's trade decisions, and the code adopts a
level an AI market owner keeps choosing after four months.

## How the tax code connects to other systems

The State of the Budget reason and the budget promise read your fixed income
and expenses, so the banking cycle and your borrowing costs (see
[Banking and monetary policy](04-banking.md)) feed into how groups judge a tax
bill. Traditionalism forbids wage and dividend taxes: under it a draft can't be
introduced while it levies either.
