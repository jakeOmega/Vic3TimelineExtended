# Three Power Bloc Identities: Creditors' Consortium, Research Commons, Dynastic Compact

Date: 2026-11-16. From the owner's brainstorm of the same day. The owner chose
the three identities, set their requirements (§ 4) and gave the Research
Commons its mechanism (§ 6.2); those rulings are marked **owner**. Everything
else is the designer's call, and the owner may revisit any of it with a stated
reason. All numbers are first guesses for the builder to tune. Nothing here is
built. Background: `docs/systems/mod_systems/power_blocs.md`,
`docs/systems/mod_systems/monetary_policy.md`,
`docs/vanilla/vanilla_diplomacy_reference.md` § 9.

## 1. Why

The mod has seven identities: vanilla's six and Diplomatic Framework. Each one
answers "what binds the members?" and carries a mechanic of its own: Trade
League's customs union, Ideological Union's regime change, Cultural
Commonwealth's Spread Primary Culture, Diplomatic Framework's Diplomatic
Alignment. Three kinds of bloc that history is full of have no identity:

- A bloc bound by **debt**, whose members keep their own markets and tariffs
  (the Ottoman Public Debt Administration, Egypt's Caisse de la Dette, the
  Marshall Plan, the IMF). Trade League can't be it: a customs union removes
  the separate budgets and tariffs the mechanic lives on.
- A bloc bound by **pooled science** (CERN, the International Geophysical
  Year, the space station).
- A bloc bound by **ruling houses** (the Bourbon Family Compact, the
  Saxe-Coburg network). Vanilla's Personal Union subject type exists and does
  almost nothing; this identity gives it a use.

## 2. Goals and non-goals

**Goals**

1. Three new identities, each with a built-in mechanic that the nearest
   existing identity's mechanic contradicts, and each with primary principle
   groups of its own (§ 3).
2. Each is built from systems the mod already has wherever one fits: the
   monetary treaty articles, the generated per-technology ladders, vanilla's
   Personal Union.
3. Each follows the design defaults in `CLAUDE.md`: one hard gate on the
   founder and on physical prerequisites, cohesion penalties everywhere else,
   and no setting worth toggling.
4. Between them they span the timeline: two from 1836, one from era 6.

**Non-goals**

- **Producers' Cartel** (tabled by the owner). Script can't set a price, so
  the premium has to come from a quota shrinking supply, and whether members
  earn more depends on the engine's price model. It needs a balance study
  before a design.
- **Climate Club** (tabled). Climate Warming is one world figure
  (`global_warming.md`), so cutting emissions is a public good and the
  Emissions Reduction article and the UN accord already cover cooperation.
  The identity needs a benefit outsiders can't share; the candidate is a levy
  on outsiders' trade in proportion to their emissions, and nobody has checked
  that script can levy trade by partner.
- **Regime Security Pact** (rejected by the owner): it is Diplomatic Framework
  with Global Security as its primary principle.
- New principle groups in detail. §§ 5 to 7 name each identity's new primary
  group and sketch its tiers; the tier tables are the builder's.
- Changing the seven existing identities.

## 3. What an identity is made of

**The test** (owner). An identity earns its place when (a) its built-in
mechanic is inconsistent with the nearest existing identity's, and (b) it has
primary principle groups of its own. An existing group with no primary
identity can become one: Advanced Research, Education, Monetary Union, Foreign
Investment and Police Coordination have none today
(`vanilla_parsed/common/principle_groups.json`,
`common/power_bloc_principle_groups/extra_power_bloc_principle_groups.txt`).
No group in vanilla or the mod is primary for two identities, and none of
these three needs one to be.

**What each new identity touches.** Diplomatic Framework is the worked
example; a new identity needs every row.

| Piece | Where | Note |
|---|---|---|
| The identity | `common/power_bloc_identities/extra_power_bloc_identities.txt` | Modifier blocks, `visible`, `possible`, `can_leave`, `cohesion`, `mandate_progress`, `ai_weight`, icon and background |
| A marker for the built-in mechanic | `common/modifier_type_definitions/power_bloc_extra_modifier_types.txt` | A `script_only` boolean on `power_bloc_modifier`, for the tooltip; script reads `has_identity`, as the monetary union reads `has_principle` |
| Primary and unlocking groups | `extra_power_bloc_principle_groups.txt` | `primary_for_identity`, `unlocking_identity` |
| The three groups with explicit unlock lists | same file: Vassalization, Colonial Offices, Sacred Civics | Each lists the six vanilla identities, so a new identity is locked out until added (§ 8.3) |
| Leader law locks | the laws' own `can_enact` | Not automatic (§ 8.1) |
| Bloc names | `common/power_bloc_names/extra_power_bloc_names.txt`, `test_power_bloc_names.py` (`IDENTITIES`) | |
| The statue method | `pm_power_bloc_statue_<identity>` in `common/production_methods/extra_pms.txt` and `unique_pms.txt` | `unlocking_identity` |
| AI invitation score | `INJECT:ai_power_bloc_identity_score` in `common/script_values/modified.txt` | |
| A summit initiative | `events/te_power_bloc_summit_events.txt`, `te_power_bloc_summit_modifiers.txt`, `test_pb_summit.py` (`IDENTITY_OPTIONS`) | One per identity (§ 8.2) |
| Subjugation strength | `common/power_bloc_identities/te_subjugation_identity_overrides.txt` | An axis or a stated "none" (§ 8.4) |
| Irredentism's leader approval | `common/scripted_triggers/irredentism_triggers.txt`, `extra_on_actions.txt` | Diplomatic Framework is exempt; these three are not |
| Icon | `scripts/image_pipeline/icon_prompts.py`, `gfx/interface/icons/central_identity_pillars_icons/` | |
| Localization | name, description, cohesion lines, marker, concept | `organize_loc.py` |
| Docs | `power_blocs.md`, the player guide's `09-diplomacy.md` § "Power bloc principles and identities", a play-test list | |

## 4. Requirements (owner, 2026-11-16)

Vanilla's pattern is thin and these follow it: one check on the founder, a law
the leader can't enact, and a cohesion cost for members who hold the wrong law
in place of a ban.

| | Unlocks | Founder must | Leader can't enact | Members |
|---|---|---|---|---|
| Creditors' Consortium | From 1836, with the National Bank law (Central Banking, era 2) | Be a valid backstop provider: a National Bank, no Command Economy, not in default | Command Economy; abolishing the National Bank | A command economy costs cohesion and gets no rescue |
| Research Commons | Era 6: Intergovernmental Organizations | Have a Ministry of Science (its law needs Nuclear Weapons, also era 6) | Abolishing the Ministry of Science | No law penalty (§ 6.6) |
| Dynastic Compact | From 1836, no technology | Be a Monarchy or a Social Monarchy | Any other governance principle, Theocracy included | An uncrowned member costs heavy cohesion and can't enter a union |

- **Game rules.** The Creditors' Consortium's mechanic is the monetary
  layer, so the identity is `visible` only under `te_mon_full_system` (the
  banking rule on Full). The owner ruled it hidden when the rule is off;
  hiding it under Simplified too is the designer's reading, since Simplified
  drops the treaty articles the rescue is made of
  (`banking_cycle.md` § "The `banking_system_simplified` game rule"). A bloc
  founded before the rule changes keeps its identity and loses the mechanic.
- **Default is a state, not a class.** Any country can leave default, so the
  founder check excludes nobody for good. A leader that defaults later keeps
  the bloc and loses most of its cohesion (§ 5.5).
- **Only a revolution ends the leader's crown.** That is the point of the
  Dynastic Compact's lock: a dominant power that founds one keeps monarchy
  alive in its bloc (owner).
- **All three need** `has_dlc_feature = power_bloc_features`, as Diplomatic
  Framework does.

## 5. Creditors' Consortium (`identity_creditors_consortium`)

Members are bound by credit. The leader stands behind their debts; a member
that defaults is rescued on terms. The owner merged the capital-transfer bloc
into this one: lending with strings and investing with strings are one
identity, and the principles chosen decide whether it plays as the Marshall
Plan or the Ottoman Public Debt Administration.

### 5.1 What contradicts what

Trade League's customs union puts members in the leader's market under the
leader's tariffs. This identity needs each member to keep its own budget, its
own debt and its own laws to impose terms on. Sovereign Empire makes subjects;
a debtor here stays sovereign and leaves receivership when its finances
recover.

### 5.2 Membership: the standing guarantee

Every non-leader member counts as backed by the leader, at the strength the
Lender of Last Resort article gives a ward
(`common/treaty_articles/112_lender_of_last_resort.txt`): its debt-load
premium is cut by `te_mon_lolr_relief`, and an imported crash starts at 0.8
severity. The build is one more branch in `te_mon_has_effective_backstop`
(`te_monetary_union_triggers.txt`): the country is a non-leader member of a
Creditors' Consortium whose leader passes `te_mon_backstop_provider_valid`
and has not suspended its guarantee.

The leader pays what a guarantor pays: a GDP-scaled share of each member's
relief as a rise in its own premium. A bloc of heavily indebted members makes
the leader's own borrowing dear, which caps the bloc's size without a rule.

Rules that follow from the existing layer:

- The relief does not stack with a treaty guarantee, a receivership or the
  Monetary Union's tier III backstop (`te_mon_has_treaty_debt_relief`).
- A member that is a command economy gets nothing, as under the articles.

### 5.3 The built-in mechanic: rescue on terms

Marker: `power_bloc_debt_administration_bool`.

**When.** A non-leader member defaults (`on_country_default`, already hooked
by `te_monetary_on_country_default`). A treaty guarantor, if the member has
one, is called first, as today. Otherwise the leader gets the consortium's
call, `te_cc.1`.

**The leader's options.**

- **Rescue on terms.** The leader pays the member `te_mon_lolr_honour_cost`
  (5% of the member's GDP, rising with each earlier call). The member enters
  the leader's receivership and takes the terms below.
- **Refuse.** The standing guarantee is suspended for every member for five
  years, the bloc loses cohesion at once, and the member stays in default. A
  guarantee is worth what the last one honored was worth; this is `te_lolr.1`'s
  Renege, without the treaty.

**The member's answer.** A player member sees the terms and may refuse them:
it stays in default, loses the standing guarantee for ten years and may leave
the bloc. An AI member accepts unless it is hostile to the leader.

**The terms.** Receivership always; then one of the others for any consortium
(owner, 2026-11-17: before that a bloc without Conditionality set none), and
as many more as the bloc's Conditionality tier adds (§ 5.4: 1, 1, 2, 2, 3 over
that base, as before), the leader choosing which.

| Term | Built from | What it does |
|---|---|---|
| Receivership | Article 114, `debt_receivership`, created by `create_treaty` with the member as source | The member pays 0.1% of GDP a month to the leader, takes −10 legitimacy and 500 leverage against it, and gets the guarantee's relief. It ends after 12 months out of default with debt under a quarter of the ceiling. The article needs International Exchange Standards (era 4); before the leader has it, a rescue carries the other terms alone |
| Structural adjustment | The engine's law imposition | While the member is in the leader's receivership, the leader may impose its own law in the economic system, trade policy and taxation groups (§ 5.3.1) |
| Concessions | `foreign_investment_rights` in the same treaty, then `acquire_monopoly_for_company` | The leader's investors may build in the member, and the leader may demand monopolies for its companies (owner). How many is the tier's figure |
| Privatization | Article 105, `enforce_privatization` | Only where the article's own `possible` passes: the member holds cooperative ownership, agrarianism or traditionalism |

A term the engine or an article's own gate rules out is not offered. A second
default under receivership fires no new call, as today.

#### 5.3.1 Imposing economic law

Vanilla's imposition runs on each law's `can_impose` block and a
`country_can_impose_same_lawgroup_<group>_in_power_bloc_bool` the imposer
holds. The mod registered two such booleans of its own (Ministry of Science,
minority rights) and reads them in its laws' `can_impose`. The laws of the
three economic groups have no `can_impose` in vanilla, so each gets one:

```
can_impose = {
	scope:target_country = {
		te_mon_is_under_receivership = yes
		var:te_mon_receiver ?= root
	}
	root = { te_cc_leads_consortium_of = { MEMBER = scope:target_country } }
	has_law = scope:law
}
```

No boolean is needed: the gate is the receivership, not a modifier. The target
gets the engine's Foreign Legal Imposition entry and the AI's `ai_impose_chance`
decides how often an AI leader uses it. If a `can_impose` added by `INJECT`
does not surface the action (§ 11), the fallback is an option on the rescue
event that runs `start_enactment` for one law the leader names.

### 5.4 Principle groups

| Group | Status | Role |
|---|---|---|
| Monetary Union | existing; becomes primary | The currency face. Its tier III backstop adds nothing to § 5.2's guarantee, by the no-stacking rule; its other effects stand |
| Foreign Investment | existing; becomes primary | The investment face |
| Development Lending | new, primary, unlocked by this identity | The Marshall Plan. Members above the bloc's average GDP per capita pay a share of their investment pool income each month to members below it (paired `add_investment_pool`, the swap line's bookkeeping). Higher tiers raise the share and add construction efficiency for the receivers |
| Conditionality | new, primary, unlocked by this identity | The Debt Administration. Tier by tier: more terms per rescue, a larger remittance, more monopoly demands, a longer receivership |

A bloc that takes Development Lending and no Conditionality rescues with
receivership and one term (its concessions carry no monopoly, since the
monopolies are the tier's) and spreads capital; one that takes Conditionality and no
Development Lending is a collection agency.

### 5.5 Cohesion, leaving, the AI

- **Cohesion.** A base; plus the leader's share of the bloc's GDP (Trade
  League's term, `power_bloc_share_gdp`); minus the leader's own debt load;
  minus worst leader relations (every identity's term); minus a step for each
  member in receivership and each command-economy member; and a large negative
  while the leader is in default. −1 per member.
- **Leaving.** Vanilla's rule (the bloc's leverage advantage over the member
  is 30 or less), and not while in the leader's receivership.
- **AI.** Founding weight from Industrialists or a financial interest in
  government, a National Bank, low debt and `ai_strategy_economic_imperialism`.
  A country with a high debt load scores a consortium's invitation up.

## 6. Research Commons (`identity_research_commons`)

Members stop researching on their own. Their universities feed the leader's
research, and what any member knows, every member knows.

### 6.1 What contradicts what

No existing identity pools research. The nearest mechanic is Science Aid
(`science_aid`, Advanced Research IV), which moves 100 innovation from one
country into another's technology spread; the Commons replaces members'
research outright. Its outside face (§ 6.5) is the opposite of the open
exchange the Knowledge Sharing pact and Science Aid stand for.

### 6.2 The built-in mechanic: pooled research (owner)

Marker: `power_bloc_research_pool_bool`.

1. **Members don't research.** The identity's `non_leader_modifier` carries
   `country_tech_research_speed_mult = -10` (−1000%).
2. **Members contribute.** Each non-leader member sends 75% of its weekly
   innovation to the leader. The share is taken after the member's own
   programs: the Space Race, the nuclear program and archaeology each take
   innovation as a weekly drain (`sr_space_program_cost`,
   `nuclear_weapon_program_funding`, `gm_arch_diversion`), and the
   contribution is 75% of what those leave. A member that raises a program's
   funding lowers its contribution; the quarter it keeps is its room to do so.
   Innovation is those programs' currency, so the Commons never takes all of
   it (owner).
3. **The leader receives.** The leader's weekly innovation rises by the sum
   of the contributions, and its innovation cap by 10% of that sum. The cap
   is what limits how fast the state of the art can move, so the fraction is
   small on purpose (owner). Innovation above the cap goes into technology
   spread, as the engine always sends it.
4. **Technologies are shared.** A technology any member holds, every member
   is granted (§ 6.3).

The leader's boost from members is the cap rise; there is no separate
research-speed bonus.

**How the contribution is applied.** Three unit modifiers, scaled by script
values: `te_rc_contribution` (`country_weekly_innovation_add = -1`) on each
member, `te_rc_pool` (`country_weekly_innovation_add = 1`) and `te_rc_pool_cap`
(`country_weekly_innovation_max_add = 1`) on the leader. There is no
`country_weekly_innovation_max_mult`, so the cap rise is an add. The preferred
carrier is a journal entry, `je_research_commons`, that every member and the
leader hold and that declares the modifiers in `scaling_modifiers_while_active`,
as the Space Race and the nuclear program declare their drains; the engine
re-reads the values every few days and nothing stacks. The entry is also where
a member sees its contribution, the pool, the leader's share and the last
technologies received. The alternative is the dynamic-modifier pattern from
the monthly country pulse.

**The contribution must not read itself.** `country_innovation` is taken to be
net of drains (`docs/testing/grand-monuments-archaeology-playtest.md`), so a
share of it shrinks month by month once the contribution is one of the drains.
Keep the amount applied in a variable (`te_rc_contributed`) and compute the
share on `country_innovation` plus that variable.

**Programs on pooled innovation.** The leader's innovation is one number, so
the pool also widens what the leader can spend on its own space and nuclear
programs. That fits the identity (CERN and the space station are the models)
and is the first thing to watch in play.

### 6.3 Sharing technologies

Script has no technology iterator and can't read a technology's era, so the
sharing is a generated ladder, one branch per technology, in the manner of
`scripts/generators/gen_covert_tech_theft.py`. A new generator,
`gen_research_commons_sync.py`, writes:

- `te_rc_sync_all`: for each technology, in prerequisite order, "if any bloc
  member has it, grant it to every member who lacks it"
  (`add_technology_researched`). Prerequisite order means a member far behind
  receives each technology after the ones it rests on, whatever the effect
  does about prerequisites.
- All three categories. The covert generator covers production and military
  only; the builder checks why before adding society.
- An exclusion list in the generator's config, empty in v1 (§ 6.7).

**When it runs.**

- On the leader's monthly pulse, for a bloc with the identity. The ladder is
  about 370 `any_power_bloc_member` checks a month per Commons.
- When a member joins: the same pass, at its first monthly pulse. There is no
  on-action for joining a bloc, so the pulse finds new members by a variable
  it sets on each (`te_rc_member`). The merge runs both ways: the bloc gets
  what the newcomer alone knew, which is a reason to recruit.
- Preferred, if § 11 confirms it: on `on_acquired_technology`, grant
  `scope:technology` to every other member at once, and keep the ladder for
  joins and a yearly sweep.

The sharing is mostly one way, since only the leader researches; members add
what reaches them by spread and by events (owner).

**A grant is not a discovery.** If `on_acquired_technology` fires for a
scripted grant, the headline and Cultural Hegemony's first-to-research hooks
must skip it. Set a variable around the grant and have those hooks read it.

### 6.4 Leaving

The owner would rather the Commons be hard to leave than ration what a
newcomer receives. In the vanilla snapshot all six identities share one leave
rule (leverage advantage 30 or less), so Sovereign Empire is no harder to
leave by definition; a harder rule is this identity's to write.

- `can_leave`: the bloc's leverage advantage over the member is 10 or less.
- A country that leaves keeps what it learned, since script can't take a
  technology away, and carries Institutes Left Behind: −50% research speed,
  decaying over ten years. The monthly pulse applies it on finding a country
  with `te_rc_member` set and no Commons.
- A newcomer receives everything at its first pulse. Membership is by the
  leader's invitation, so the leader chooses whom to teach.

### 6.5 Principle groups

| Group | Status | Role |
|---|---|---|
| Advanced Research | existing; becomes primary | Raises the caps the pool fills |
| Education | existing; becomes primary | Raises members' literacy, and so the innovation they send |
| Technology Controls | new, primary, unlocked by this identity | The outside face: open among members, closed to everyone else |

The engine's technology spread is one country-wide figure with no source, so
script can't stop an outsider's spread from drawing on what members know.
Technology Controls works on what script does own:

- members may not give Science Aid or Knowledge Sharing to non-members;
- members' defense against covert technology theft rises by tier;
- from a middle tier, the leader may place a Technology Embargo on one
  country: a pact that cuts the target's `country_tech_spread_mult`, sized by
  the bloc's share of the world's innovation.

### 6.6 Cohesion and the AI

- **The leader must be the bloc's best researcher** (owner). The main term is
  the leader's own innovation, before the pool, as a share of the bloc's.
  Without it the best play for a leader is to close its universities and let
  the members pay, the opposite of the theme. The monthly pulse stores the
  share on the leader (`te_rc_leader_share`) and the `cohesion` block reads it
  through `scope:power_bloc.power_bloc_leader`. The previews for a country
  joining or leaving read the stored figure unchanged.
- Also: a base; minus worst leader relations; −1 per member.
- **No law penalty for members.** The Ministry of Science law needs Nuclear
  Weapons, which most members will hold only because the Commons shared it. A
  penalty for lacking the ministry would punish every newcomer.
- **AI.** Founding weight from Intelligentsia in government, the Ministry of
  Science and `has_global_highest_innovation`. An invitation scores up by how
  many technologies the leader holds that the target lacks (`techs_researched`),
  and down for a great power.

### 6.7 Every technology, weapons included

The founder holds Nuclear Weapons (the ministry law needs it), so every member
gets it at its first pulse and may open a nuclear program. A program still
costs innovation for years, and a member keeps a quarter of its own. V1 shares
everything; the generator's exclusion list is the lever if play shows the
Commons arming the world. A technology on the list would reach a member only
by the leader's act.

## 7. Dynastic Compact (`identity_dynastic_compact`)

A bloc of monarchies bound by their ruling houses. The house is fixed, not the
laws, which is what sets it against Ideological Union.

### 7.1 What contradicts what

Ideological Union's leader changes a member's regime and imposes its laws.
This leader changes nothing in a member's laws; it joins the member's crown to
its own. Sovereign Empire needs a monarchy to found and takes subjects by
force (`possible = { country_has_monarchy_law = yes }`); here the members must
be crowned too, and a union comes by inheritance or by agreement.

### 7.2 Crowned

One trigger, `te_dyn_crowned`, used for the founder check, the member penalty
and every union gate: the country has the Monarchy law or the Social Monarchy
law (owner: nothing else, so no Theocracy). Vanilla's Personal Union pact
keeps a rule of its own on both sides, `country_has_monarchy_law = yes` and
not the Shogunate (`law_bakufu`), and a union needs that as well. The body of
`country_has_monarchy_law` is not in the snapshot (§ 11); if it is exactly
Monarchy and Social Monarchy with their variants, use it and drop the new
trigger.

### 7.3 The built-in mechanic: dynastic union

Marker: `power_bloc_dynastic_union_bool`.

Facts this rests on, from the vanilla snapshot:

- The Personal Union diplomatic action has `potential = { always = no }`.
  Nothing in the interface creates one; only script does
  (`create_diplomatic_pact = { type = personal_union }`, or
  `change_subject_type` on an existing subject). Vanilla's own decisions copy
  the overlord's governance law onto the junior first.
- A junior uses the overlord's ruler, joins its wars, can't start its own
  plays and can't change its governance principles at all
  (`lawgroup_governance_principles`' `change_allowed_trigger`). A great power or
  an unrecognized major power can't be a junior; a major power can.
- The union ends when either side stops passing the pact's monarchy rule.
- A subject follows its overlord's bloc and is not counted among the
  independent members that cost cohesion.

So a union is this identity's reward and its glue: the junior's crown is
locked, and each union removes a member's cohesion cost.

**Two ways in**, both between the leader and an independent, crowned member
of a rank that can be a junior, in the bloc five years:

- **By consent: Offer a Union of Crowns.** A leader's diplomatic action that
  needs approval. The AI weighs the bloc's leverage over it, relations, how
  far the leader's prestige exceeds its own, its own legitimacy (a shaky
  throne wants a strong one) and a house tie (§ 7.4), against its rank and
  differences of religion and heritage. On acceptance the member takes the
  leader's governance law if it differs and the pact is created.
- **By succession: a Succession Pact.** A two-sided pact between leader and
  member, easier to get than a union because it costs nothing today. While it
  stands, the member's heir is the leader's ruler (`set_heir`, the primitive
  vanilla's `amend_succession` article uses for Brazil and Portugal, with the
  displaced heir kept aside as that article keeps him). When the member's
  ruler dies, the union forms. If the leader's ruler dies first, the pact
  points the member's succession at the new one. Breaking the pact restores
  the displaced heir.

Neither way is a war goal, so the nuclear and UN rules about
`make_personal_union` don't apply.

**What a union leads to.** Vanilla already lets an overlord reduce a union's
autonomy once it has Nationalism, and annexes a union when its overlord forms
a country (`annex_on_country_formation = yes`). The identity adds nothing there in
v1; a peaceful annexation of a long-held union belongs to the Dynastic Ties
group's top tier, beside Vassalization IV's for puppets.

### 7.4 Cadet branches (second phase)

There is no dynasty object in script. Vanilla marks a few houses with a
character variable; whether an heir inherits it is unknown. The Compact tracks
a house on the country: `te_dyn_house`, pointing at the leader whose house
holds the throne, cleared when the country stops being crowned.

**Place a Cadet Branch.** The leader's action on a crowned member that is in a
regency or has no heir: the member gets an heir of the leader's house (a new
character with the leader's ruler's family name) and `te_dyn_house`. A member
of the leader's house counts for cohesion and is readier to accept a union or
a Succession Pact. This is the second build phase: it rests on the most
unverified character scripting, and the unions work without it.

### 7.5 Principle groups

| Group | Status | Role |
|---|---|---|
| Police Coordination | existing; becomes primary | The security state that keeps the thrones (owner). Tiers IV and V already unlock Security Aid, the mod's "help a regime survive" article |
| Dynastic Ties | new, primary, unlocked by this identity | Legitimacy for crowned members, readier acceptance of pacts and unions, lower liberty desire in unions; at the top, peaceful annexation of a long-held union |

### 7.6 Cohesion, leaving, the AI

- **Cohesion.** A base; plus the leader's legitimacy (Ideological Union's
  term); plus a step for each member of the leader's house; minus a heavy step
  for each uncrowned member; minus worst leader relations; a large negative
  while the leader is uncrowned or in a regency. −2 per member, and a union is
  no longer a member.
- **A member's revolution.** A member that loses its crown stays in the bloc
  and costs the heavy step; a junior that loses it has its union ended by the
  engine. Nothing expels anyone.
- **Leaving.** Vanilla's rule. A junior follows its overlord.
- **AI.** Founding weight from Landowners in government and the monarchy
  laws; a crowned country scores an invitation up and an uncrowned one far
  down.

### 7.7 What the rest of the mod already does with unions

Read before building; none of it needs changing for v1.

- The UN suspends a Personal Union junior's membership and bills its dues to
  the overlord (`un_membership_triggers.txt`). A Compact that gathers unions
  loses UN votes.
- A junior keeps its own monetary arrangement
  (`te_monetary_arrangement_triggers.txt`).
- Seabed Administer Claims excludes juniors.
- Heir Education (`heir_education.md`) reads `law_monarchy` and the heir. A
  member under a Succession Pact has the leader's ruler as heir; the entry
  should pause for it.

## 8. Shared parts

### 8.1 Leader law locks

Vanilla does not derive these from the identity's `possible`. Each locked law
says so itself: National Militia's `can_enact` is "not a bloc leader, or the
bloc is not a Military Treaty Organization". So each row of § 4's "Leader
can't enact" column is a clause in those laws' `can_enact`:

| Identity | Laws that get the clause |
|---|---|
| Creditors' Consortium | `law_command_economy`, `law_no_national_bank` |
| Research Commons | `law_no_ministry_of_science` |
| Dynastic Compact | every law of `lawgroup_governance_principles` but Monarchy and Social Monarchy, the mod's two included |

Most of these laws have a `can_enact` already. Whether a second block added by
`INJECT` is read with the first is unverified (§ 11); the fallback is to
restate the law.

### 8.2 Summit initiatives

One each, in `te_pb_summit.1`, at the scale of the seven there:

| Identity | Initiative | Effect for ten years |
|---|---|---|
| Creditors' Consortium | Debt Conference | Members: a lower risk premium; member relations |
| Research Commons | Scientific Congress | Members: +10% weekly innovation, which the pool then takes its share of |
| Dynastic Compact | Family Gathering | Members: base legitimacy; leader relations |

### 8.3 The three groups with explicit unlock lists

| Group | Creditors' Consortium | Research Commons | Dynastic Compact |
|---|---|---|---|
| Vassalization | yes | no | yes |
| Colonial Offices | yes | no | yes |
| Sacred Civics | no | no | yes |

Research Commons stays out of all three, as Diplomatic Framework does.

### 8.4 Subjugation strength

Each vanilla identity pays a bonus to the mod's Subjugate when the target
matches its axis. Creditors' Consortium gets one,
`country_subjugation_creditor_strength_add = 0.4`, paid when the target is in
the leader's receivership: Egypt went from the Caisse de la Dette in 1876 to
British occupation in 1882. Research Commons gets none, as Diplomatic Framework has none. Dynastic
Compact gets none: its union is its own way to a subject. The Subjugation
Strength concept quotes the axes as text and needs the new line.

## 9. Build order

One PR per identity, each whole (§ 3's table): the identity, its markers, its
primary groups with the new group's tiers, the law locks, names, statue,
summit initiative, AI, localization, icon, tests, docs, the player guide
subsection and play-test rows.

1. **Creditors' Consortium.** Most of it exists; the new script is the call
   event, the treaty it creates, one trigger branch and two principle groups.
2. **Research Commons.** A generator, a journal entry and the monthly pulse.
3. **Dynastic Compact**, in two phases: unions (§ 7.3), then cadet branches
   (§ 7.4). Start with a debug console event that probes § 11's union facts.

## 10. What's left to the builder

- Every number: shares, steps, thresholds, durations, cohesion weights, AI
  weights.
- The tier tables of the four new groups (Development Lending,
  Conditionality, Technology Controls, Dynastic Ties) and their technology
  gates, to the pattern of the existing fifteen.
- The journal entry's layout for the Research Commons, to
  `docs/guides/gui_style_guide.md`.
- Bloc names, statue methods and icons for the three.
- Whether a player member's refusal of rescue terms needs a cooling-off rule.
- The usual obligations: a section in `power_blocs.md`, the player guide,
  American English localization through `organize_loc.py`, the audits clean,
  a play-test list (`docs/testing/power-bloc-identities-playtest.md`).

## 11. Engine facts to verify

Ship the preferred version with a once-a-game `TE_SELF_CHECK` line where the
build rests on one of these (`CLAUDE.md`, "In-game checks"), and name the
fallback in the play-test list.

| # | Fact | Used in | Fallback |
|---|---|---|---|
| 1 | `create_treaty` with `debt_receivership` enters into force without a war, runs the article's `on_entry_into_force`, and does not need the article's technology or `can_ratify` | § 5.3 | Set the receivership's role variables directly, as the treaty-transfer helper's fallback does |
| 2 | A `can_impose` added to a vanilla law by `INJECT` makes the engine offer the imposition | § 5.3.1 | `start_enactment` from the rescue event |
| 3 | `create_treaty` can carry `acquire_monopoly_for_company` with its company and building inputs chosen by script | § 5.3 | The leader proposes it in the treaty screen; the member's AI accepts while in receivership |
| 4 | `country_innovation` reads as a value, net of drains, and how often it updates | § 6.2 | Band it with trigger comparisons, as `nuclear_exchange_values.txt` does |
| 5 | A member at −1000% research speed still receives technology spread | § 6.2 | A smaller penalty, or none and a larger contribution |
| 6 | `add_technology_researched` grants a technology whose prerequisites are missing | § 6.3 | None needed: the ladder runs in prerequisite order |
| 7 | `add_technology_researched = scope:technology` works, and `on_acquired_technology` fires for scripted grants | § 6.3 | The monthly ladder alone |
| 8 | `scope:power_bloc.power_bloc_leader.var:<name>` reads in a `cohesion` block | § 6.6 | A bloc-scope modifier the pulse scales |
| 9 | `create_diplomatic_pact = { type = personal_union }` works between two existing independent countries, with the governance law copied first | § 7.3 | `je_marea_unire` does it in vanilla; none expected |
| 10 | `set_heir` with another country's ruler works outside Brazil and Portugal, and what the engine does when the member's ruler then dies | § 7.3 | The pact forms the union on `on_character_death` by script |
| 11 | The body of `country_has_monarchy_law` | § 7.2 | `te_dyn_crowned` as written |
| 12 | A second `can_enact` block added by `INJECT` is read with the law's own | § 8.1 | Restate the law |
| 13 | What a civil war does to a union, a Succession Pact and bloc membership | § 7.6 | Rebuild from variables, as `What a Civil War's Winner Inherits` prescribes |

## 12. The owner's rulings, 2026-11-16

1. The identity test of § 3, including that an existing principle group may
   become a new identity's primary.
2. Creditors' Consortium and the capital-transfer bloc are one identity.
   Rescue terms include economic laws, a share of income and monopolies.
3. Research Commons: members lose their research and send most, not all, of
   their innovation; the leader's cap rises by a small fraction of it, 10%;
   technologies are shared on a pulse or on acquisition; hard to leave; the
   leader's share of the bloc's innovation drives cohesion.
4. Dynastic Compact: Monarchy and Social Monarchy only; the security state is
   a principle group; a dominant Compact may keep monarchy alive past its
   historical end.
5. Requirements as § 4; Creditors' Consortium hidden with the banking rule off.
6. Producers' Cartel and Climate Club tabled; Regime Security Pact rejected.
