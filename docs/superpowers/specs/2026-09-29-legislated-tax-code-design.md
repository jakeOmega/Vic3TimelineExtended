# Legislated tax code and customs schedule — design specification

**Date:** 2026-09-29 (America/Denver)  
**Status:** proposed design; no gameplay implementation in this change  
**Scope:** replace the existing tax-law/rate split with one enacted fiscal code

## 1. Purpose and agreed direction

The player assembles the tax code they want, sees its economic and political consequences,
negotiates concessions, and passes the resulting package. Raising a rate, cutting a rate,
moving a consumption tax from grain to automobiles, and granting a capital exemption are all
changes to legislation. Their scale changes the process, not whether political approval exists.

This replaces the existing taxation-law progression. It is not an extra layer of configurable
rates constrained by the vanilla tax laws (Land-Based, Per-Capita, Consumption-Based, Proportional,
or Graduated Taxation). Those names may remain as descriptive labels or drafting presets, never as
restrictions that predetermine the schedule.

Tariffs belong to the same fiscal code, in a dedicated Customs and Trade section. A bill can
change one provision or many; a customs-only bill need not reopen the entire domestic schedule.

The central gameplay is deciding who pays, what the revenue enables, and whose consent is
needed. The design targets a rich simulation first, with explicitly labeled fallbacks where
engine capabilities are insufficient. No engine feasibility claim is implied by a desired control.

### Design invariants

1. One authoritative enacted schedule; drafting never changes collections.
2. One bill can bundle multiple provisions into one political bargain.
3. All ordinary changes, including cuts and repeal of concessions, require approval.
4. Executive adjustments are permitted only by powers already granted in law.
5. Defeat, withdrawal, elections, and government collapse do not erase existing taxes.
6. Public approval, actor preferences, political commitments, and passage are distinct.
7. Every material support contribution has an inspectable reason.
8. Economic effects must charge an identifiable payer; a tax is not free treasury income.
9. The AI and player use the same legal constraints and collection rules.
10. Reduced granularity is an acceptable fallback; disconnected free tax toggles are not.

### What this document does not settle

Exact rates, technology gates, political weights, durations, implementation identifiers, and
performance budgets require prototypes and balancing. The illustrative party example is not a
balance table. Detailed parliamentary/presidential institutions remain a separate system; this
spec defines their interface and a fallback when that system is absent.

## 2. Existing foundations and integration points

These are existing repository references, not a claim that the proposed system is implemented:

- [Amendments](../../../common/amendments/extra_amendments.txt): sponsors, allowed laws,
  modifiers, conditions, and repeal restrictions.
- [Temporary amendments](../../systems/mod_systems.md#temporary-amendments-sunset-clauses):
  timed concessions and expiry handling.
- [Legislative override capacity](../../../common/laws/legislative_override_capacity.txt):
  government-dependent ability to bypass normal procedure.
- [Banking](../../player_guide/04-banking.md): fiscal balances already feed the cycle.
- [Climate](../../player_guide/14-climate.md): an existing carbon-tax policy must be reconciled,
  not stacked with a second independent fiscal control.
- [Economy reference](../../vanilla/vanilla_economy_reference.md#12-taxes-and-government-revenue):
  existing income, dividend, consumption, land, and per-capita channels.
- [GUI style](../../guides/gui_style_guide.md): Budget tab, shared journal widgets, open
  dynamic information, short labels, detailed tooltips, one collapsed explanation section.
- [System reference](../../systems/mod_systems.md): snapshot-driven GUI reads and state
  reconstruction after revolutions.

The existing land-tax channel must not be presented as a true tax on landowners' land values.
Dividend taxes must not be relabeled wealth, inheritance, or corporate-profit taxes.

## 3. Fiscal code and bill model

Conceptually separate these records, whatever storage the engine supports:

| Record | Required contents |
|---|---|
| Enacted code | Version, provisions, operative dates, delegated powers, collection rules |
| Bill | Base code version, sponsor, changed provisions, revision, stage, proposed commencement |
| Provision | Instrument, tax base, rate/amount, coverage, exceptions, precedence, duration |
| Commitment | Actor, bill revision, conditions, promised action, circumstances allowing release |
| Estimate | Economy snapshot date, code/bill revision, method, coverage, uncertainty |
| Legislative result | Required authorities, recorded decisions, assent, pending commencement |
| Scheduled transition | Provision identity, date, successor rule, later amendments that supersede it |

A bill is a patch to a complete code. Unchanged provisions remain visible but need not be
renegotiated individually. Review always compares the complete resulting code with the enacted one.

Proposed initial scope: one active legislative tax bill per country, plus one editable draft.
This controls bookkeeping, not the number of clauses a bill may contain. Reconcile a draft with
any intervening enacted change before introduction; do not silently overwrite a newer code.

### Lifecycle

Enacted code -> draft -> introduced -> negotiation/debate -> required votes and assent ->
approved, awaiting commencement -> effective.

A draft may be discarded freely. Introduced bills may be revised, withdrawn, defeated, or lapse.
Minor revisions reopen affected commitments; substantial revisions extend debate and may require
renewed chamber approval. Any required chamber approves the same final text. A late rewrite
cannot retain votes obtained for a materially different bill.

A failed or withdrawn bill leaves the enacted code intact. A parliamentary confidence defeat
may change the government but never switches collection off. Elections recalculate representation
and commitments; whether a pending bill lapses follows the constitutional procedure.

At commencement, validate and apply the package together. There must be no observable interval
with both old and new taxes applied, or with all taxes removed. Persist a recoverable code version.

Sunsets are execution of previously approved law, not fresh executive decisions. Each specifies
an explicit successor (for example, 30% dividends returns to 15%). If a later law replaces that
provision, the obsolete sunset must not restore an outdated rate. An approved phase-in follows
the same rule.

## 4. Player GUI: Budget > Tax Code

The system's natural home is a Tax Code tab in the Budget window. Compose reusable sections
for this tab and the journal entry; the latter can carry status and an Open Budget action.
Follow the existing GUI style guide rather than introducing a separate visual language.

### 4.1 Enacted view

Always-visible overview: code name, effective date, total collections, next scheduled change,
and active bill status. Show current rates and active privileges, with amendment/sponsor details
available from each provision. Actions: Draft reform, Resume draft, View bill, View history.

Opening or inspecting the window is read-only. Selecting a preset or changing a value requires
an explicit drafting action. History lists enacted changes, sponsors, concessions, and expiries.

### 4.2 Workbench layout

| Area | Contents |
|---|---|
| Header | Bill name, sponsor, draft/revision status, enacted baseline version |
| Left navigation | Income; Ownership; Business; Consumption; Land/Property; Head Taxes; Special Levies; Territories; Customs; Exemptions; Administration; Commencement |
| Center editor | Current -> proposed values, effective burdens, clause-specific exceptions |
| Right consequences | Switch between Economics and Politics without losing edits |
| Persistent summary | Revenue delta, budget balance, required approvals, earliest commencement |
| Footer actions | Review changes, save draft, discard draft, introduce/revise bill |

Use short labels and tables for live figures. Shares use the house-style share display; progress
toward passage uses a threshold marker. Dynamic content remains open. Place general instructional
text in one collapsed How Tax Legislation Works section.

Narrow layouts may replace columns with category pages, but preserve the summary and draft state.
Disabled actions expose all failing conditions in their tooltip. Important disagreements and
treaty conflicts also appear in the review page; they must not exist only on hover.

### 4.3 Provision editors

| Instrument | Ideal controls and feedback |
|---|---|
| Personal income | Allowance, editable marginal brackets/rates, wage-indexed or fixed thresholds; representative effective burdens |
| Ownership income | Separate dividend schedule or inclusion in income; cooperative distribution treatment |
| Business profits | Profit rate, small-business threshold, reinvestment allowance, loss carryforward |
| Consumption | Default/category rates, searchable goods, individual overrides, necessities exemptions |
| Land/property | Land value versus improvements; agricultural/urban treatment; smallholding and residence allowances |
| Head taxes | Amount, assessed population, exemptions; monetary units instead of percentage-rate controls |
| Special levies | Emissions, extraction royalties, windfall profits, inheritance, net wealth, temporary wartime surcharges |
| Territorial provisions | Selected states, capital relief, colonial treatment, regional sharing |
| Customs | Import and export duties, category/good overrides, delegated bands; controls and authority in section 6 |
| Administration | Enforcement funding, anti-avoidance measures, compliance and collection costs |
| Commencement | Effective date, phased steps, fixed expiry, explicit successor rules |

The Exemptions page lists every clause from the structured editor below, whichever instrument it
modifies. Start with discrete rate steps and expandable advanced settings, not dozens of mandatory sliders.
Final precision depends on balancing. A tax bracket is marginal: crossing it cannot retroactively
tax all income at the higher rate. Show effective rates beside marginal rates.

Goods can inherit category defaults. Each exception remains visible beneath its parent. A
structured clause editor reads: For [eligible group] in [territory], change [instrument] by
[amount/rate], until [date]. It exposes supported selectors, not unrestricted script expressions.

Every exception displays beneficiary population/economic activity and foregone revenue.
Precedence must be deterministic and inspectable. Proposed rule: instrument default, category
override, explicit good/base override, then eligible relief. Multiple relief clauses affecting
the same base require an explicit combine-or-replace rule; ambiguous overlaps block introduction.
Separate legal instruments may both apply, but their total incidence must be shown.

### 4.4 Review and negotiation views

Review groups additions, changes, repeals, unchanged provisions, future steps, treaty conflicts,
collection requirements, and spending commitments. Every row shows its current and successor rule.
The introduction action states that present collections remain unchanged until commencement.

During debate, show a revision log and actors' offers. Previewing an offer shows its clause diff,
revenue change, and political changes across all actors. Accepting it creates a new revision and
records the commitment. Removing its condition reopens that commitment.

After passage, show the effective date and future steps. After defeat, offer revise/reintroduce
subject to procedure, retaining the draft; never silently enact the desired settings.

## 5. Economic consequences

Provide Treasury, Households, Businesses, and Regions views.

| View | Required information |
|---|---|
| Treasury | Gross assessments, collection losses, net receipts, administration cost, total budget balance, phase-in/expiry effects |
| Households | Change in tax paid and disposable income, by income, occupation, state; winners and losers within strata |
| Businesses | Profits, production/input exposure, ownership distributions; distinguish profit taxes from output levies |
| Regions | Burden, privileges, industry exposure, shared revenue or funded benefits |

Separate a current-economy estimate from a medium-term forecast. The first applies both schedules
to one dated snapshot; the second reports ranges and causal explanations, not exact predictions.
Display when a proxy or incomplete coverage limits an estimate.

Distinguish the legal payer from expected economic incidence. A tariff paid at import is not
assumed to fall wholly on foreign producers, and a business tax is not assumed to fall wholly on
owners. Avoid claiming an exact price/employment pass-through without an economic model.

Technology and administration determine available instruments and collectability. Collection
capacity is not a substitute taxation-law ladder. Complex codes can cost more to administer,
but do not punish every additional GUI clause regardless of real complexity.

Let existing disposable-income, market, investment, and banking effects operate. Do not add a
generic high-tax growth penalty that duplicates them. Fiscal purposes require funded commitments:
a label reading "for education" cannot generate free support or fictitious spending benefits.

## 6. Customs and Trade

Tariffs are provisions of the enacted code. Customs-only bills use the same workflow and
political model as mixed reforms.

Controls: default import duty, default export duty, category/good overrides, partner preferences,
temporary duties, and delegated authority. Import protection and export restrictions have distinct
beneficiaries. Import and export settings never share an unexplained multiplier.

| Action | Authority |
|---|---|
| Establish or materially change duties | Legislation, alone or bundled with domestic taxes |
| Create goods/partner exemptions | Legislation unless expressly delegated |
| Adjust within a legislated band | Executive action within the granted range and conditions |
| Anti-dumping or retaliation | Temporary executive action only under an enabling provision, with limits and expiry |
| Treaty tariff ceiling/preference | Treaty approval by the constitutional process; binding on later ordinary actions |

Delegation records eligible goods/partners, direction, range, trigger conditions, duration, and
renewal/review rules. Emergency declarations cannot create unlimited tax discretion by themselves.

Show applicable treaties next to each constrained setting. An incompatible bill cannot silently
break a treaty: require a separate explicit withdrawal/breach choice and its diplomatic consequences,
or block introduction pending the necessary diplomatic action. A pending treaty or customs-union
change invalidates conflicting previews and triggers revalidation before enactment.

Customs-union/market authority must be respected: only the competent country can set shared duties.
Members see imposed provisions and provenance; they cannot override them through a domestic bill.
Exact integration depends on the engine and existing treaty/market mechanics.

Support uses combined consumption-tax and tariff incidence. Exempting grain domestically while
raising its import duty must not automatically earn a food-affordability bonus.

Tariff coalitions depend on actual production, consumption, and input exposure: grain growers
versus consumers; steelmakers versus machinery users; extraction exporters versus domestic
downstream industry. An automobile duty need not remain a luxury policy as ownership spreads.

Retain Trade Policy laws only for institutional rules, delegation, treaty approval, or entrenched
restrictions. If they merely encode tariff levels, replace that function with the schedule.
Embargoes and non-fiscal diplomatic restrictions remain diplomatic instruments.

## 7. Political support and opposition

### 7.1 Three layers

1. Populations develop preferences from burden, expected benefits, ideology, and circumstances.
2. Parties, IGs, movements, and regional blocs aggregate interests through their actual composition.
3. Constitutional rules translate representation and power into required approvals.

Do not count the same constituents twice as independent party and IG votes. Public approval is
population-based; electoral pressure follows franchise rules; legislative strength follows seats
or the selected fallback. Wealth-related lobbying is separate from votes and must not manufacture
additional voters.

People excluded from the franchise still experience hardship, mobilize, strike, or support
enfranchisement. Autocracy changes approval mechanisms, not whether affected people have interests.

### 7.2 Actor evaluation

Evaluate the complete proposed code against the current code. An actor can prefer the reform
without considering its outcome ideal. Absolute ideological red lines may still apply.

Conceptual score for actor a:
S(a) = material burden + ideology + fiscal stance + sector + region + administration
       + relationships + election salience - transition/timing costs - distrust.

This is an explanatory decomposition, not settled arithmetic. Components must have bounded,
documented scales and actor-specific weights. Material and sectoral components must not count
the same modeled income loss twice; sectoral terms cover distinct risks/interests.

| Driver | Inputs | Required behavior |
|---|---|---|
| Material burden | Disposable-income/profit/rent/wealth changes relative to resources | Losses matter more where resources are scarce; coverage matters, not just nominal rates |
| Ideology | Progressivity, property rights, equal treatment, national protection, environmental aims | Actors may accept personal costs for principles |
| Fiscal stance | Debt service, deficit, reserves, public-service commitments | Tax cuts can lose support; crisis funding can gain it |
| Sector | Domestic competition, exports, input prices, employment exposure | Owners and workers within a broad class can disagree |
| Region | Local burden, privileges, industry, revenue sharing | Territorial bargaining has real beneficiaries and costs |
| Administration | Reporting burden, complexity, enforcement, avoidance | Simple broad taxes can appeal more than complicated low nominal rates |
| Timing | War, recession, implementation speed, recent changes | Phase-ins and genuinely temporary measures alter support |
| Trust | Broken concessions, revoked promises, misuse of emergency powers | Sunsets and compensation depend on credibility |
| Relationships | Coalition agreement, opposition incentives, discipline | Policy preference and promised vote can diverge |
| Elections | Franchise, competitiveness, salience | Public reaction affects representatives unequally |

Model ideology with several preferences rather than one high-tax/low-tax axis. A fiscal liberal
may support a broad, simple tax to avoid insolvency while opposing exemptions. Agrarians can favor
progressivity yet reject a land assessment. Conservative actors can support wartime revenue and
defend inherited privilege simultaneously.

Purpose benefits reference actual spending or enforceable commitments with costs and deadlines.
Breaking such a commitment has explicit trust/political effects. Never award support solely for
selecting a rhetorical justification.

### 7.3 Preference, salience, and commitment

Keep separate: substantive preference, issue salience, willingness to bargain, and vote commitment.
A modest loss on a vital livelihood can be more salient than a larger diffuse benefit elsewhere.
Party discipline converts internal dissent into delivered votes only with internal/electoral costs.

Actor cards show firm support, persuadable support, and opposition; they expose top reasons and
affected clauses. Exact future votes are not guaranteed unless an enforceable commitment supports
them. Any uncertainty is declared and stable between meaningful updates, not rerolled by opening
the GUI.

Demands have three levels: preference, condition for commitment, and red line. Accepted offers
specify clauses and duration. A concession can alienate other actors. Prevent approval farming
through repeated trivial edits or cycling identical concessions.

### 7.4 Political institutions

| Arrangement | Passage behavior |
|---|---|
| Parliamentary | Coalition negotiation; major defeat threatens confidence only under applicable rules or an explicit confidence designation |
| Presidential | Required chamber approval and executive assent/veto rules; rejection retains the existing code |
| Bicameral | Separate chamber constraints; money-bill powers depend on the constitution, not an automatic symmetric veto |
| Direct democracy | Major reforms go through the relevant popular process; minor discretion must be delegated |
| Autocratic | Imposition is easier where authorized; elite, administrative, and popular resistance remain |
| Constitutional monarchy | Use its actual parliamentary/executive arrangements, not the monarchy label alone |

No routine mandatory annual reauthorization. Elections, crises, and reform opportunities generate
tax politics without requiring the player to repass the same code every year.

Before a full republic system exists, aggregate IG/party support and legitimacy into a journal-based
passage process. Label this honestly; do not imply simulated seats where none exist. Bypass options
integrate legislative override capacity and expose authority costs and political consequences.

## 8. Illustrative negotiation scenario

A government proposes dividend-tax increases, basic-food exemption, and a pollution levy.
Urban workers favor food relief; extraction workers fear job losses. Owners of clean industry
and fossil production differ. Liberals accept the revenue need but dislike privileges.
Agrarians ask for smallholding relief; fiscal conservatives support debt reduction but oppose
the incidence of the package.

A phased pollution levy, targeted transition spending, and a smallholding allowance may produce
a majority. They also reduce net revenue and can lose liberal support. Compare all changes at once.
Under parliament, defeat may challenge confidence; under a presidency it may leave a rejected bill
and an unchanged fiscal position. Neither event suspends existing collection.

## 9. Law amendments and state ownership

Preferred representation: a persistent Tax Code law with script-managed amendments describing
operative provisions, supported by a canonical schedule where additional detail is needed.
Rate bands are mutually exclusive; exemptions are separate clauses. Do not let native amendment
repeal bypass the bill process or let independent AI amendment behavior alter the enacted schedule.

Amendments may carry effects directly when valid. Otherwise they document the operative rule and
synchronized scripts apply it. Declare exactly one source of truth and one effect application path.
Every display, native tax control, scripted event, and AI action reads or changes that same schedule.

Mirror recoverable authoritative state as required by the repo's revolution-inheritance rules.
Rebuild missing modifiers/amendments idempotently. Preserve enactment dates and remaining durations;
reconstruction must not restart sunsets or replay political rewards.

The existing carbon-tax control must become an entry into this process or reflect an authorized
shared-market policy. Audit its market-wide scope before migration; do not silently convert another
country's imposed policy into domestic discretion. Retire duplicate fiscal effects explicitly.

## 10. AI, performance, and continuity

AI proposes packages to address revenue needs, ideology, constituency interests, and crises. It
evaluates complete packages and the same offers as players. Use bounded candidate templates and
local improvements rather than searching every combination. Templates are drafting aids, not laws.
Reform benefit must exceed political/administrative costs; use hysteresis to prevent oscillation.

Do not give AI states free collections or bypass constraints to compensate for weak planning.
Protect solvency through plausible compromise, borrowing, spending responses, and legal emergency
powers rather than silently setting rates.

Compute expensive incidence and support aggregates on dated snapshots and meaningful revisions.
Do not enumerate all world pops in per-frame GUI getters. UI reads cached results; refresh visibly
when needed. Save/load must preserve the operative code, draft, bill stage, commitments, and dates.

Initial migration maps current law, tax level, consumption selections, and tariffs into the nearest
supported code while preserving receipts/burdens as closely as possible. Any approximation is
reported. Disable or reroute old rate buttons, tax-law AI, events, and effects to avoid a second
control path. Migration is versioned and idempotent.

Proposed continuity default: the winner of a revolution continues the country's enacted tax code
and dates, reconstructs collection effects, and revalidates political commitments/pending bills.
New constitutions can require a pending bill's reintroduction. Territorial changes re-evaluate clause
eligibility and customs authority. Specify whether an exemption follows the capital designation or
a named state at drafting time; moving the capital must not create an accidental exploit.

If a game-rule fallback is provided, choose mode at campaign setup initially. Mid-save disabling
requires an explicit tested reverse migration and is not assumed safe.

## 11. Feasibility gates and fallbacks

All rows are implementation investigations, not verified engine limitations.

| Desired feature | Investigation | Acceptable fallback |
|---|---|---|
| Arbitrary brackets/allowances | Payer-specific tax bases and modifiers | Named schedule catalog with limited parameters and honestly labeled incidence |
| Independent consumption rates | Per-good rate control and authority handling | Selected goods with one common rate or supported category bands |
| Corporate profits, wealth, inheritance | Actual bases, payer deduction, treasury transfer | Omit unsupported instrument; do not relabel a different tax |
| Land-value tax | Landowner value versus peasant assessment | Explicitly named existing rural assessment; defer genuine land-value taxation |
| Territorial/sector taxes | Valid scope, affected payer, collection behavior | Supported state/building mechanisms with clear limitations |
| Household preview | Income/tax/consumption data access | Representative households and broad distribution bands |
| Medium-term forecast | Validated behavioral model | Static estimates plus directional risks |
| Legislators/constituencies | Representation and election integration | Party/IG blocs, support shares, separate public approval |
| Ideology vectors | Traits and actor composition | Explicit tax preferences on existing ideologies |
| Spending bargains | Binding budget/institution commitments | Small catalog of enforced, costed commitments |
| Native legislative workflow | Votes, assent, amendment lifecycle | Journal-based negotiation and passage |
| Amendment representation | Cardinality, exclusivity, automatic repeal/AI | Major amendments plus canonical variables/effects |
| Tariff partner preferences | Treaty/market control and differentiation | Supported goods/direction controls; do not promise unenforceable partner exemptions |
| Rich workbench | Native binding, controls, safe draft state | Category pages/shared journal widgets with persistent summary |

Before implementation, test the native tax-level buttons, consumption-tax authority costs,
law-stance and movement dependencies, modifier scope/application timing, treaty controls,
tax-base observability, and the order in which tariffs and Trade Advantage resolve (an open
question in the [economy reference](../../vanilla/vanilla_economy_reference.md#143-tariffs-and-subventions)).
Authority reservation may need reconciliation with legislated consumption taxes; neither preserve
nor remove it silently without a documented balance decision.

## 12. Delivery sequence

1. Feasibility and compatibility spikes: establish payable bases, control interception, amendments,
   tariffs, snapshots, and persistence. Record supported/fallback choices.
2. Canonical schedule and migration: reproduce the current economy before adding new powers.
3. Workbench and estimates: draft/review without economic mutation; native control reconciliation.
4. Bundled passage: explainable actor support, offers, commitments, enactment, sunsets.
5. Customs integration: tariff-only/mixed bills, treaties, delegation, shared-market authority.
6. Institutional integration: parliamentary/presidential/direct-democracy procedure.
7. Advanced instruments and forecasts where evidence supports them.
8. AI/balance/save validation and updated player guide/PDF with the actual implemented behavior.

Do not treat this sequence as approval to ship unverified advanced instruments. Each implementation
PR records its deviations and fallbacks. A first playable release must still satisfy the invariants.

## 13. Acceptance criteria for implementation

### Code and lifecycle
- Editing, previewing, saving, and discarding drafts do not alter collections or political rewards.
- Failed/withdrawn bills, elections, and confidence defeats retain current taxes.
- Passage applies the approved revision only after all required approvals and commencement.
- Rate cuts, exemption removal, and customs changes cannot bypass the procedure.
- Small and large bills differ in procedure cost without making small changes politically free.
- Later revisions invalidate relevant commitments/approvals; no last-minute substitution exploit.
- Phase-ins/sunsets survive reload and revolution; superseded sunsets do not restore old provisions.

### Economics and politics
- Estimates compare schedules against the same snapshot and identify approximations.
- Marginal brackets do not create all-income tax cliffs.
- Each instrument has an identifiable base, payer, revenue path, and collection cost.
- Combined tariff/consumption effects prevent contradictory affordability rewards.
- Party and IG aggregation does not double-count votes or economic harm.
- Narrow franchise changes electoral influence without erasing disenfranchised opposition.
- Sectoral coalitions can divide both workers and owners; concessions can lose support elsewhere.
- Spending promises require real costs; broken promises and revoked concessions matter.
- Public approval, policy preference, commitments, and constitutional passage remain separate.

### Customs and integration
- Import/export duties are distinct; tariff-only and mixed bills both work.
- Delegated actions enforce eligibility, limits, trigger, expiry, and successor rules.
- Treaty conflicts require explicit handling; members cannot override shared customs authority.
- Carbon-tax and native tax controls have one operative source of truth.
- Fiscal effects do not duplicate the existing banking/disposable-income response.
- Migration is idempotent and documents economic discrepancies.

### UI, AI, and persistence
- Current versus proposed versus pending settings are unambiguous.
- Review exposes every changed provision, beneficiary, expiry, and legal constraint.
- Actor detail traces support to clauses; disabled controls explain their conditions.
- Narrow resolutions/localization do not hide passage requirements or primary actions.
- AI uses the same constraints, avoids reform oscillation, and can negotiate viable packages.
- Opening the GUI does not mutate simulation state or cause expensive per-frame world sweeps.
- Save/load, revolution, capital relocation, territorial transfer, and market changes have
  scenario coverage before release.

## 14. Remaining decisions

- Exact precision, brackets, rates, caps, administrative costs, and technology progression.
- Political component weights, salience scaling, commitment release rules, debate timing.
- How to represent spending commitments without turning this feature into a full expenditure editor.
- Constitutional delegation defaults and specific upper-house money-bill powers.
- Which engine fallbacks are required after prototypes.
- Native consumption-tax authority treatment and reverse migration, if supported.
- The mapping of existing Trade Policy laws and tax-related ideology/movement demands.
- Whether the system ships behind a game rule, as the mod's major systems do, and what the
  disabled mode keeps (section 10 assumes a campaign-setup choice if so).

The repository's current player guide describes implemented systems. This specification alone
does not change gameplay and does not require rebuilding that guide; implementation PRs do.
