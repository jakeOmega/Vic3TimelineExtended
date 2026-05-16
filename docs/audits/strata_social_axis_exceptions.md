# Strata vs social-axis audit — exceptions

This file lists events whose mirrored upper/lower-strata radicals + loyalists shape is **genuinely the economic content of the event**, not a proxy for social-progressivism. The `strata_social_axis_audit.py` script reads this file and moves listed events from the unexempted to the exempted bucket of `docs/audits/strata_social_axis_report.md`.

**Format:** one bullet per event, with the event id in backticks at the **start of the line**, followed by two sentences of mechanical context explaining why the strata reaction is the real economic content. Don't write one-word category labels — the goal is for this doc to double as the reference for "when *is* strata-targeted reaction actually correct?".

**Format example:**

> - `` `banking_cycle_events.12` `` — Defending the gold peg deflates wages and rewards creditors who get repaid in stronger currency, so upper-strata loyalist and lower-strata radical reactions reflect direct asset-vs-wage incidence. Abandoning gold inflates debt away, flipping the same incidence — upper-strata radicals (asset holders) and lower-strata loyalists (debtors and wage earners). This is creditor-vs-debtor economics, not a social-progressivism proxy.

---

## Banking / financial cycle

The banking-cycle event chain models monetary policy choices (gold standard defence vs devaluation, central-bank stance, bailout politics, asset-bubble incidence) where upper-strata pops are asset/creditor holders and lower-strata pops are wage earners and debtors. The strata flip is direct economic incidence; rewriting these to IG/movement reactions would lose the asset-vs-wage signal that the system is built around.

- `banking_cycle_events.1` — Recession-onset choice between austerity and stimulus. Austerity protects bondholders (upper) and depresses wages (lower); stimulus inflates the way out, hurting creditors and helping debtors. The strata flip is asset-vs-wage incidence, not a social-progressivism proxy.
- `banking_cycle_events.3` — Bubble-pressure response: tighten credit (upper-strata creditors win, lower-strata borrowers lose) vs let it run (debtor relief, creditor loss). Standard asset-vs-debt cycle incidence.
- `banking_cycle_events.4` — Bailout politics: option .c specifically rewards lower-strata depositors via deposit guarantees while bondholders take losses. The strata reaction is incidence of who the bailout protects.
- `banking_cycle_events.6` — Currency-stability defense; option .b carries the standard creditor-protection / wage-deflation incidence.
- `banking_cycle_events.10` — Liquidity crisis response. Option .a's lower-radical / upper-loyalist split reflects emergency liquidity injections that protect bank balance sheets but inflate prices for wage-earners.
- `banking_cycle_events.11` — Boom-cycle interest-rate decision; tightening punishes borrowers (lower), accommodation punishes creditors (upper). Standard cycle incidence.
- `banking_cycle_events.12` — Gold standard defence vs devaluation, with the classic creditor-vs-debtor incidence flip across options. (See worked example above.)
- `banking_cycle_events.13` — Industrial overinvestment response: defending profits vs letting bubble correct. The strata reaction tracks asset-holder vs wage-earner exposure to the correction.
- `banking_cycle_events.17` — Cycle-stage panic response; options trade creditor protection vs broad relief, with strata reactions tracking who bears the cost.
- `banking_cycle_events.18` — Asset-deflation politics with within-option mirrored incidence — the policy choice itself sets winners and losers.
- `banking_cycle_events.19` — Multi-option bailout / reform menu where each option's strata reaction reflects which class bears the policy cost.
- `banking_cycle_events.30` — Recovery-phase tightening vs continued accommodation. Standard asset-vs-wage incidence flip.
- `banking_cycle_events.31` — Bubble-onset choice. Tightening protects deposits and asset prices; loosening lets the boom run with the wage/debtor side benefiting.
- `banking_cycle_events.32` — Same cycle decision shape with the strata incidence reflecting who pays for the policy.
- `banking_cycle_events.34` — Asset-bubble peak intervention. Option .a's upper-radical / lower-loyalist split reflects intervention that crashes asset prices but cushions wages.
- `banking_cycle_events.36` — Late-cycle reform choice. Option .c targets asset-holder losses with debtor relief — direct redistribution incidence.
- `banking_cycle_events.39` — Recession recovery option that protects creditor confidence at the cost of broad employment — option .c's upper-loyalist / lower-radical reflects that creditor-first policy.
- `banking_cycle_events.42` — Panic-stage politics with mirrored options for bondholder-protection vs broad bailout.
- `banking_cycle_events.44` — Multi-option monetary choice with class-incidence reactions per option.
- `banking_cycle_events.50` — Cycle peak choice between bubble continuation and prudent contraction. Same asset-vs-wage flip.
- `banking_cycle_events.53` — Frenzy-stage intervention with explicit class incidence per option.
- `banking_cycle_events.104` — Late-cycle policy switch; options carry asset-holder vs debtor incidence.
- `banking_cycle_events.117` — Bubble correction politics with strata reactions reflecting bankruptcies (upper losing) vs wage protection (lower gaining loyalty) or the inverse.
- `banking_cycle_events.151` — Cycle-onset policy choice with cycle-standard incidence.
- `banking_cycle_events.154` — Currency policy that rewards bondholders at the cost of debtors (option .c specifically reflects that).
- `banking_cycle_events.160` — Recession-response option with explicit asset-holder loss vs wage-earner relief signal.
- `banking_cycle_events.167` — Recovery option with the standard creditor-vs-debtor incidence flip.

## Anti-war / conscription incidence

Anti-war movement events model the class incidence of conscription and war financing, not a social-progressivism axis. Lower-strata pops bear the conscription draft directly while upper-strata pops largely escape it; war-profit policy directly hits or shields industrial capital. The strata reactions reflect who pays the war's cost, which is genuine economic incidence rather than a class proxy for pacifist sentiment.

- `movement_events_te.5` — Draft Resistance. The lower-strata radicalism from hunting deserters tracks working-class anger at conscription enforcement (they are the ones at risk); lower-strata loyalty on alternative-service reflects relief from that same draft pressure. This is class incidence of conscription policy, not a pacifism proxy.
- `movement_events_te.6` — Veterans Speak Against the War. Lower-strata reactions track who the war's casualties fell on (overwhelmingly working-class draftees) and whose families are most affected by suppression of veteran testimony; officer reactions track the institutional military stake. The signal is war-cost incidence by class, not pacifism-by-class.
- `movement_events_te.7` — Peace Rally Fills the Capital. Suppressing the rally radicalizes lower-strata pops because they were the ones most likely to attend (working-class draftees and their families). The strata reaction reflects who bears the cost of being denied political voice over the war policy that conscripts them.
- `movement_events_te.8` — War Profiteering Exposed. Strata reactions directly track who benefits from the war contracts (upper-strata industrial capital) vs who bears the social cost (lower-strata conscripts and consumers facing wartime prices). Investigating war profiteers radicalizes the capital owners being investigated; dismissing the complaints radicalizes the working-class taxpayers funding the contracts. Pure capital-vs-labor incidence on war financing.

## Augmentation access inequality

- `movement_events_te.10` — The Augmentation Divide. The event's frame is explicitly economic — neural augmentation as a scarce expensive good that only the wealthy can buy, with the policy choice being whether to subsidize broad access or let market forces sort it. Lower-strata loyalty on subsidies reflects who gains material access; upper-strata radicalism reflects who pays via taxation. The strata reaction is capital-vs-labor incidence over augmentation as an economic asset, not a transhumanist-social-axis proxy. The mod's broader transhumanist-attitude axis lives in `movement_events_te.9` / `.11` / `.12` (which use clergymen/academics/engineer pop-type reactions instead).
- `augmentation_events.2` — Same augmentation-access axis as movement_events_te.10. Lower-strata radicalism without access to augmentation reflects exclusion from an emerging economic good; upper-strata loyalty reflects retained competitive advantage. Class incidence of augmentation availability, not a transhumanist-social-progressivism proxy.
- `augmentation_events.3` — Workplace Discrimination based on augmentation status. The lower-strata signals across options track who keeps or loses jobs to augmented competitors — protecting unaugmented workers makes them loyalist (they keep their jobs); letting the market sort it radicalizes them (they get fired in favor of cheaper augmented workers). The strata reaction is labor-market displacement incidence, equivalent in shape to any other technology-displacement event (mechanization, AI, etc.).
- `augmentation_events.5` — Augmentation regulation in response to augmented crime. Option .b's upper-loyalist / lower-radical reaction tracks who carries risk from augmented criminals (the unaugmented working-class, who can't physically defend against augmented attackers) vs who benefits from continued unrestricted augmentation (the augmented well-off). Personal-security incidence by augmentation access, not a social-progressivism proxy.

## Economic-political corruption events

These events model the political economy of corporate power and money-in-politics, where strata reactions track who owns / benefits from the corrupting actor (upper-strata holds the capital being lobbied for) vs who pays the social cost (lower-strata bears the externalities). The reactions are economic-incidence, not a social-progressivism proxy.

- `social_tensions_events.3` — Corporate Lobbyists in the Legislature. Strata reactions per option track which class's interests the legislative outcome serves — protecting / regulating / appeasing lobbyists shifts the capital-vs-labor incidence directly.
- `social_tensions_events.4` — Monopoly Power. Trust-busting vs accommodation has the standard antitrust incidence — capital owners radicalize when their monopoly is broken; working-class consumers and small businesses benefit. Pure capital-vs-labor on market structure.
- `social_tensions_events.9` — Campaign Finance Scandal. The strata flip tracks who benefits from continued legal big-money politics (upper-strata donors who buy access) vs who's effectively disenfranchised (lower-strata voters). Political-economy incidence, not a social-axis question.
- `social_tensions_events.10` — Big-Money Election. Same shape as .9 — strata reactions track who the dollar-vote favors. Capital-amplified political power incidence.
- `social_tensions_events.15` — Globalization Backlash. Free trade vs protectionism is the textbook capital-vs-labor incidence event — embracing free trade rewards upper-strata capital owners (cheap imports, export-led growth) while displacing lower-strata workers; protective tariffs flip the incidence. The strata reactions track real trade-policy distributional consequences, not a social-progressivism proxy.
- `society_technology_events.9` — Outsourcing Wave. Standard free-trade vs protectionism incidence — upper-strata capital owners gain from outsourcing, lower-strata workers bear job-displacement cost. Mirror of `social_tensions_events.15`.
- `society_technology_events.10` — Anti-Globalization Protests. Same capital-vs-labor incidence shape. Trade-policy distributional consequences.
- `society_technology_events.16` — The Neural Interface Rollout. Augmentation-access-as-economic-good incidence (lower-strata cannot afford the implants without subsidies). Same shape as `augmentation_events.2` / `movement_events_te.10`.
- `society_technology_events.17` — The Augmented Athlete Scandal. Personal-stakes incidence of competitive disadvantage from being unable to afford augmentation. Augmentation-access economic axis.
- `society_technology_events.19` — Space Colony Governance Crisis. The strata signals track colonist labor vs colonial administration / shareholder interests — classic colonial economic-extraction incidence at orbital scale.
- `society_technology_events.23` — Nuclear Meltdown. Safety/health incidence — lower-strata workers and downwind communities bear the radiation exposure, upper-strata reactor owners face liability and asset writedowns. Public-health-vs-asset incidence, not a social-progressivism proxy.
- `society_technology_events.24` — Anti-Nuclear Movement. Same nuclear-incidence axis as .23 — strata reactions track who bears health risk vs who owns the assets.
- `society_technology_events.27` — Algorithmic Governance Proposal. Strata reactions track who benefits from administrative efficiency (upper-strata: streamlined regulation, asset protection) vs who bears algorithmic accountability gaps (lower-strata: opaque welfare/criminal-justice decisions). Bureaucratic-incidence axis.
- `society_technology_events.30` — The Self-Driving Revolution. Labor-displacement incidence — lower-strata drivers lose jobs, upper-strata vehicle owners gain via cheaper fleet operation. Standard technology-displacement economic shape.
- `society_technology_events.31` — The First Fatal AV Crash. Liability and safety incidence — lower-strata victims and adjacent workers bear physical risk, upper-strata vehicle owners and manufacturers bear liability. Tort-incidence axis, not a social-progressivism proxy.

## Decolonization (colonial economic incidence)

Decolonization events model the wind-down of colonial economic extraction. Upper-strata reactions track the colonial / metropolitan administrative class and overseas investors (who lose extraction returns); lower-strata reactions track the colonized population and metropolitan working class (who bear conscription / lose colonial-job remittances or gain liberation). The strata flip is colonization-incidence, not a social-progressivism proxy. (The mod's social-axis decolonization framing lives in `un_events.12`, which is already IG-targeted.)

- `decolonization_events.4` — Independence-grant choice with the standard colonial-administrator vs colonized-population incidence flip.
- `decolonization_events.6` — Insurgency-response choice; strata track who pays the counterinsurgency cost vs who benefits from a negotiated settlement.
- `decolonization_events.7` — Three-option independence-process choice with the same colonizer-vs-colonized incidence shape across options.
- `decolonization_events.15` — Settler-population crisis; strata reactions track settler-vs-indigenous incidence directly.
- `decolonization_events.16` — Colonial-asset disposal; strata track who loses or retains the extracted wealth.
- `decolonization_events.18` — Late-stage transition logistics; strata-asymmetric reactions reflect the unequal capacity to relocate or repatriate capital.
- `decolonization_events.21` — Post-independence economic-policy choice; strata reactions track the residual colonial-economy stake.

## Environmentalism (pollution-vs-jobs incidence)

Environmental-policy events model the textbook environmental-economics distributional axis — green regulation hits polluting heavy industry (upper-strata asset owners) while protecting workers and neighborhoods from pollution-health-cost (lower-strata exposure). Lax policy flips both: industry retains profits, workers and downwind communities bear the health cost. The strata reactions track real pollution-incidence, not a social-progressivism proxy.

- `environmentalism_events.2` — Green-regulation vs industry-protection incidence shape. Strata flip tracks the underlying pollution-vs-asset distributional tension.
- `environmentalism_events.5` — Same shape; environmental policy hits polluting industry while protecting affected workers / neighborhoods.
- `environmentalism_events.7` — Same shape.
- `environmentalism_events.9` — Same shape.
- `environmentalism_events.10` — Same shape; the within-option mirrors at L745/L780 track who pays vs benefits from each policy direction.
- `environmentalism_events.11` — Same shape.
- `environmentalism_events.12` — Same shape.
- `environmentalism_events.13` — Same shape.
- `environmentalism_events.14` — Same shape.
- `environmentalism_events.15` — Same shape.

## Extra-law amendment events (economic / language-incidence)

- `extra_law_events.2` — Run on the Banks (Financial Regulation – panic angle). Banking-panic incidence: upper-strata depositors face frozen accounts and asset writedowns; lower-strata savers bear deposit-loss risk. Same shape as banking_cycle exceptions.
- `extra_law_events.25` — State-Led Language Reform Founding. The six flagged sub-options (`a_pali`, `a_chinese`, `a_irish`, `a_nahuatl`, `a_mayan`, `b`, `c`) each represent a different script-choice; the strata reactions track the dominant-culture working-class reaction to script disruption (a real cultural-economic cost), not a uniform social-axis assumption. The Chinese option's inversion confirms the audit is detecting cross-script variation, not the bug-class proper.
- `extra_law_events.26` — Language Academy. Same script-choice incidence as `.25` at amendment time.
- `extra_law_events.27` — Voices From the Margin. Minority-script preservation amendment; the strata signals reflect which cultural group bears the script-transition cost vs benefits from script-retention.
- `extra_law_events.31` — Data Privacy amendments (Corporate Data Exemption vs Whistleblower Shield). Corporate-vs-public-data axis is economic — capitalists win on exemption, lose on shield. Reactions track real economic-incidence of data-asset control.
- `extra_law_events.33` — Small Donors, Big Voices (Electoral Finance amendment). Campaign-finance incidence — small-donor matching dilutes capital-owner political power; rejecting it preserves the dollar-vote advantage. Standard money-in-politics economic axis.
- `extra_law_events.36` — Radical Law Backlash. Reactions are already IG-targeted per backlash type (devout, landowners, industrialists, petty bourgeoisie, etc.); the strata signals are proportional to the IG signals and track the actual economic class affected by each radical-law type (communal child rearing, command economy, etc.).

## Heir education

- `heir_education_events.2` — Tutor selection. Strata reactions track which class's worldview shapes the heir's future governance (military tutor → upper-class war-state preference; populist tutor → lower-class redistributive preference). This is an elite-formation event, not a social-progressivism proxy.
- `heir_education_events.3` — Education-policy emphasis. Same elite-formation shape; strata reactions track which class's interest the heir will favor when they rule.

## Mental health (treatment-cost incidence)

Mental health policy events model treatment-access and institutional-cost trade-offs. Upper-strata reactions track who pays for state-funded mental-health programs via taxation; lower-strata reactions track who benefits from access to treatment they couldn't otherwise afford. The strata flip is health-economic incidence, not a social-progressivism proxy.

- `mental_health_events.2` — Mental-health-treatment access-vs-cost shape; upper-strata pays for state programs while lower-strata accesses treatment otherwise unaffordable.
- `mental_health_events.3` — Same shape.
- `mental_health_events.4` — Same shape.
- `mental_health_events.5` — Same shape; the within-option mirror at L404 tracks treatment-funding incidence directly.

## Modern election events

- `modern_election_events.8` — Election-campaign tactical choice. Strata reactions track which class's votes the campaign cultivates (populist appeal grows lower-strata turnout; elite-coordination strategy consolidates upper-strata backing). Electoral-coalition incidence, not a social-progressivism proxy.
- `modern_election_events.16` — Mobilization-vs-suppression strategy. Strata track who is being mobilized or excluded.
- `modern_election_events.18` — Late-campaign messaging choice with the standard electoral-coalition strata signal.

## Post-scarcity, repeatable, treaty, wonder, space race, world war

These events model various economic / wartime / construction / diplomatic incidence patterns where strata reactions track who pays for and who benefits from the policy at hand. None are social-progressivism proxies.

- `post_scarcity_events.4` — Post-scarcity transition; strata reactions track who loses positional advantage from abundance (upper-strata capital owners) vs who gains material security (lower-strata consumers).
- `repeatable_events.30` — Periodic event with the same incidence shape repeated across firings.
- `space_race_events.35` — Space-program funding politics. Upper-strata reactions track the tax-cost of the program; lower-strata reactions track the prestige / jobs-program benefit.
- `space_race_events.50` — Late-stage space-race milestone with the same funding-cost-vs-prestige incidence shape (option .b and .c flip the cost-bearer per choice).
- `treaty_article_events.4` — Treaty-clause incidence; strata reactions track which class's interests the diplomatic concession protects or sacrifices.
- `treaty_article_events.10` — Same shape; different clause type.
- `wonder_events.3` — Space-elevator gateway open vs restricted; strata reactions track who benefits from open access vs sovereign restriction.
- `wonder_events.11` — Wonder-construction incidence (taxation cost vs domestic-prestige benefit).
- `wonder_events.23` — Wonder-construction incidence; specific wonder type.
- `wonder_events.31` — Wonder-construction incidence; specific wonder type.
- `world_war_events.10` — War-mobilization and war-finance event. Strata reactions track conscription-incidence (lower-strata draftees), war-tax incidence (upper-strata bond purchases), war-profit incidence. Mirror of anti-war exemption rationale above.
- `world_war_events.11` — Same war-cost incidence shape.
- `world_war_events.12` — Same war-cost incidence shape.
- `world_war_events.30` — Same war-cost incidence shape.
- `world_war_events.101` — Same war-cost incidence shape; receiving-side event.
- `world_war_events.102` — Same war-cost incidence shape; receiving-side event.

## UN intervention cost incidence

These UN events model strata reactions to who pays for international intervention vs who gains from declining it — the costs (military deployment, foreign aid) fall on upper-strata taxpayers, the savings from declining accrue to them. Distinct from refugee / human-rights events in the same file, which are social-axis and were rewritten.

- `un_events.4` — Peacekeeping Mission Deployed. The strata reactions are tagged "Military costs" in-source and track who pays for deployment via taxation (upper-strata radicalize when deployed, become loyal when declined). Pure fiscal-incidence of military intervention abroad.
- `un_events.101` — Humanitarian Aid Received. Lower-strata loyalist gain on grateful acceptance reflects who actually consumes the aid (food, medical, infrastructure benefits flow to working-class recipients); upper-strata loyalist gain on sovereign-assertion framing reflects elite political stake in preserving pride. Both directions track real material vs symbolic distribution of the aid event's payoff.
- `un_events.102` — Peacekeeping Forces Deployed to Our Territory. Lower-strata loyalty on welcoming peacekeepers tracks who benefits from the resulting stability (working-class neighborhoods see less war damage); upper-strata loyalty on resenting the intervention tracks the sovereignty / nationalist-pride stake. Material-benefit vs sovereignty-pride incidence, not a social-progressivism proxy.
- `un_events.103` — International Refugee Resettlement. Lower-strata loyalty on accepting the relief reflects domestic ease of refugee-pressure on working-class neighborhoods; upper-strata loyalty on the humiliation framing reflects sovereign-pride stake. Same intervention-receipt shape as `.101` / `.102`.
