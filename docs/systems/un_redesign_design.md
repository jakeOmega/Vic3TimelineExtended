# United Nations Redesign — Design

> **STATUS: DESIGN AGREED IN OUTLINE, NOT IMPLEMENTED.** Written 2026-09-24 from a design
> discussion with the mod owner. It follows a survey of the UN as it stands (§1) and a
> bug-fix pass that shipped first (§1.4). Decisions the owner made are marked **(decided)**.
> Everything else is **(proposed)**: a starting shape to implement and tune, not a ruling.
> Items marked **VERIFY IN-GAME** cannot be proven from files. Every number is a starting
> point, and the numbers are collected in [§13](#13-tuning-constants).
>
> The current system is documented in [`journal_entry_systems.md` § United Nations](journal_entry_systems.md).
> This document describes where it goes next. Mandates, standing and lobbying all survive
> the redesign; §10 says how each one plugs in.

---

## 0. The goals in one paragraph

UN authority should read like a **verdict on the state of the world**, not like the sum of
two hundred countries' coin flips. It should rise when the powers that matter invest in the
institution and it delivers, and fall when they walk away, defy it or go to war around it.
**Its extremes should be hard to reach but reachable.** A sole superpower should be able to
drag the UN to either end over decades. At the top, the UN reshapes the game: acting outside
it is ruinous, and its institutions carry game-changing effects, good and bad. At the
bottom, it dissolves. **Everything it does costs someone something.** It should be tied to
the situations that actually occur (wars, famines, collapses, nuclear use, exposed
operations, crashes), and its effects should be visible **in the places where they
happen**. **Everything the Assembly does to a country must be explainable to that
country**: why it was tabled, why members voted as they did, and what it will cost.

---

## 1. Where the system stands (survey, 2026-09-24)

### 1.1 Authority is moved by who acts, not by the state of the world

`global_var:un_authority` (0–100) is one number. Almost every change is a **flat delta
applied no matter how big the actor is**. A micro-state withdrawing from arms control moves
world authority exactly as much as a superpower doing the same.

| Source | Size | Frequency |
|---|---|---|
| Programme toggles (human rights, arms control, peacekeeping, development) | ±2–3 per toggle, **no cooldown** | Any member with the qualifying law can toggle; the AI toggles as it enters and leaves wars |
| Standalone random events (`un_events.4/5/7/8/10/11/13/15/20`) | ±1–5 | about 7–10 a year worldwide |
| Declined vote-proposer events | +1 / −1 to −3 | about 1–2 a year |
| Vote outcomes (`un_vote.2`) | +5 / +10 on a pass, −3 on a fail, −5 on a veto | about 1 a year (the vote lock holds the floor for 365 days) |
| Systematic drift (`un_authority_drift_total`) | toward 50 at ±0.25/month (only outside 45–55); member wars up to −3/month; champion/undermine ±0.3–0.5/month per GP; bloc alignment | monthly |

Two mechanisms actively **resist** the extremes:
- the pull toward 50;
- `un_events.10`, which fires for **every** great power while authority is below 25 and
  mostly adds +3 to +5 each time.

History: `un_authority` began as a per-country variable and was converted to a global
(`docs/superpowers/plans/2026-07-06-un-authority-global-variable-fix.md`). The per-actor
flat deltas were written for the per-country model and were never rescaled when every
actor started writing to one shared number.

### 1.2 Resolutions never scale with authority

- **Every resolution modifier is flat.** Only membership benefits
  (`× authority/50`), `un_high_authority_infamy_modifier`, non-member pariah status (≥ 60)
  and NPT disarmament (≥ 80, non-nuclear members only) read authority.
- **The conventions all give the same thing.** Human rights, heritage, pandemic, climate,
  refugee, space and law of the sea each give nearly every member a permanent +3–5%
  prestige and a small ministry bonus, so the relative effect is roughly zero.
- **Most agencies do nothing.** Six of the nine agency globals only feed the display.
- **The climate accord has no emissions effect.** `un_climate_binding_modifier` carries no
  `country_greenhouse_gas_emissions_mult`.
- **Nothing is state-scoped.** Peacekeeping and aid are country-wide modifiers; the only
  local UN effect is the headquarters building's state modifier.

### 1.3 Nearly everything is upside, and most events are generic

- **Joining costs nothing, and the conventions are pure bonus.**
- **Every vote-proposer event has a free exit:** "+1 authority, nothing else".
- **Several defiant options pay very well:** `un_events.13.a` and `20.c` grant +250
  domestic Authority; `3.c`, `16.c` and `102.b` grant +100.
- **Only three events describe a real situation:** condemnation of an actual aggressor (2),
  sanctions enforcement (5) and the authority crisis (10).
  - The peacekeeping event sends a contributor to a random war anywhere.
  - The humanitarian trigger ("any state anywhere below SoL 8") is always true.
  - The treaty topics are gated only by technology and authority.
- **Covert warfare, cultural hegemony, state collapse and banking have no UN link at all.**

### 1.4 Bugs fixed before the redesign (shipped on this branch, commit `958de82`)

- **Aid and peacekeeping pledges were free.**
  - The aid cost was stripped monthly by `legacy_je_modifier_cleanup_effect`.
  - The peacekeeping levy recomputed the cost in journal-entry scope, where `gdp` reads
    `'none'`, from a loop whose ROOT was another country.
  - Pledges are now charged at pledge time, in `un_vote.3`.
- **A vetoed reform still paid out.**
- **Leaving the UN lifted sanctions against the leaver**, and kept the aid prestige
  marker while dropping its cost.
- **Vetoed sanctions gave the target the enforcer's token-compliance modifier**, which
  grants +2% leverage. The target now gets its own modifier.
- **`un_events.4`'s duplicate check looked at the wrong country**, and `un_events.5` could
  act on an empty scope.

Deliberately left for the redesign, because the phases below rewrite the code involved:
- Treaty proposers keep their modifier when the vote fails.
- The lifetime pledge counters make the AI permanently reluctant to vote aid.
- `un_expelled_cooldown` is never applied.
- The on_action and event triggers disagree for events 2, 8 and 12.
- The aid-recipient modifier's inline multiplier reads `prev.var:temp_giver_gdp`, which
  does not survive re-evaluation.
- The defiant options' domestic Authority payouts.
- The "compliance" modifiers pair +15% infamy decay with +10% infamy generation. The
  pattern is consistent enough to read as intended ("the moral high ground brings
  scrutiny"), but the redesign should decide it on purpose.

---

## 2. Principles

1. **Weight by power.** Every country-caused change to authority is scaled by that
   country's share of world power (§3.1). Rounding a micro-state to zero is correct.
2. **Lasting change lives in the pillars; headlines fade.** Authority approaches an
   equilibrium computed from the world (§3). A direct shock moves the value but not the
   equilibrium, so it decays unless the world changed underneath it.
3. **Strength means reach, not just size.** High authority changes *what* a resolution
   does (a trade penalty becomes an embargo), not only its multiplier (§5).
4. **Nothing is free.** Every benefit has a payer or a loser, and every event option has a
   cost.
5. **Explain everything to the country it happens to.** A punitive resolution needs
   grounds that can be read on the card. Every vote comes from one itemised lean that the
   chamber can print (§6).
6. **Situations, not dice.** UN business arises from real situations, is addressed to the
   countries involved, and names the place (§8).
7. **Local effects are local.** Missions sit in states and show in the state panel (§9).
8. **One implementation per rule.** The AI and the display read the same script values;
   no rule is restated in a second place that can drift (the house rule already used by the
   chamber and mandates).

---

## 3. Authority as a verdict on the world

### 3.1 Power share (decided: prestige)

`un_power_share` is `prestige / Σ prestige` over every country that is neither decentralized
nor unrecognized. **(decided: prestige, because it folds GDP in with rank, military and
standing)** The global UN pulse computes it once a month and caches it as a country variable,
because both the pillars and the display read it. **(proposed)**

### 3.2 The equilibrium (target) **(proposed)**

`un_authority_target` is the sum of the pillars below, clamped to `[0, charter cap]`
(§4.1). The global pulse computes it monthly and stores it for display.

| Pillar | Range | Computed from |
|---|---|---|
| **Base** | 20 | constant |
| **Participation** | 0 … +20 | `20 × Σ power_share` of members |
| **Great-power commitment** | −25 … +25 | `25 × Σ stance × power_share` over every country. Stance: champion **+1**, member **0**, undermine **−1**, a non-member of major-power rank or above **−0.5**. A member's stance also gains `country_un_institutional_alignment` (the Multilateral Institutions bloc principle), so that hook survives |
| **Credibility** | −15 … +15 | a rolling record of binding decisions enforced vs. defied, vetoed or ignored (§3.4) |
| **Funding** | −10 … +10 | the share of assessed dues actually paid, weighted by the size of each assessment (§7.2) |
| **Peace & order** | −20 … 0 | wars between members weighted by power share (the existing `un_member_wars_weight` shape, made power-weighted); aggression without a mandate; nuclear use. Each decays |
| **Delivery** | 0 … +10 | missions concluded successfully in the last ten years, minus failed ones, weighted by mission size (§9) |

The existing drift components fold into the pillars:
- champion and undermine → commitment;
- member wars → order;
- institutional alignment → commitment;
- the humanitarian-law "democracy" bonus → dropped, or folded into credibility
  **(proposed: dropped)**.

### 3.3 Approach, and what a shock is **(proposed)**

- **Approach.** Each month authority moves toward the target by `(target − authority) /
  un_authority_approach_months`, capped at `±un_authority_max_step` a month. With 48 months
  and a 1.0 cap, a jump of 40 in the target closes by half in about 2.8 years.
- **World moments** change authority directly and rarely: a permanent member leaving, a
  nuclear strike, the Assembly ending a great-power war, a veto crisis. They are headlines.
  The value then drifts back toward the target unless the moment also moved a pillar, and
  most do (a defied resolution is a credibility entry; a strike is an order entry).
- **Nothing else writes `un_authority`.** Programme toggles, per-country events and votes
  move pillars in proportion to the actor's power share. All writes go through two helpers,
  in the shape `un_standing_gain` / `un_standing_loss` already use, so the audit trail is
  one grep.

### 3.4 The credibility ledger **(proposed)**

A global list of entries, each carrying a sign, a weight and a timed decay (15 years), in
the same capped-list shape as `un_resolution_history`.
- **Credit:** a binding resolution carried *and* complied with (the target complied, or
  was sanctioned and the regime held); an authorised mandate discharged as written; a
  sanctions regime that ends with the target's compliance.
- **Debit:** defiance of a binding resolution; a veto, weighted by the vetoer's power
  share; a violated mandate; a sanctions regime collapsing under busting; a resolution that
  lapsed because nobody enforced it.
- **Weighting:** each entry is weighted by the power share of the actor who earned it. A
  superpower defying the Assembly is a crisis; a minor one is a footnote.

### 3.5 Worked examples (to hold tuning against) **(proposed)**

**A normal multipolar world.** 90% of power in the UN, stances mostly neutral, dues paid,
some small wars, a few missions.
`20 + 18 + 0 + 0 + 10 − 5 + 3 = 46`.

**A sole superpower, all in.** 40% of world power; member, championing, paying,
enforcing; two allies championing.
- `20 + 19 + 12.5 + 10 + 10 − 2 + 8 = 77.5`.
- That is capped at 70 until the first charter reform (§4.1).
- With the reforms, other great powers eventually championing, full credibility and
  delivery, it reaches `95`.
- That is decades of work, and other permanent members can veto the reforms along the way.

**The same superpower, all out.** It has left, is undermining, and wages wars without
mandates.
- `20 + 11 − 5 − 10 + 2 − 10 + 0 = 8`.
- That opens the dissolution crisis (§4.3) within a few years, unless others step in.

The owner's test: **(decided)** a sole superpower must be able to push the UN to either
extreme within decades. The swing between the last two examples is about 70 points.

### 3.6 Display **(proposed)**

- **Journal-entry header:** actual vs. target, the charter cap, and a one-line "why it is
  moving".
- **Pillar breakdown:** one bar per pillar with its value, and for the two power-weighted
  pillars the three largest contributors by name.
- **History chart:** authority and target, using `te_history_record_global_sample` and the
  existing `te_history_chart` widget. The chart's recipe in `mod_systems.md` § "History
  Store and Charts" already anticipates a UN series.
- **World-moment markers** on that chart (`te_history_record_global_marker`).

---

## 4. The ladder, the ceiling and the floor

### 4.1 Tiers and charter caps **(proposed)**

| Tier | Authority | Enforcement `E` | Character |
|---|---|---|---|
| **Moribund** | < 20 | 0 | Resolutions are recommendations only. A veto costs nothing. Power blocs fill the vacuum: bonus to bloc cohesion and leverage |
| **Contested** | 20–45 | 0.5 | Today's UN, roughly |
| **Established** | 45–70 | 1.0 | Binding resolutions bite |
| **Strong** | 70–85 | 1.5 | Needs **Charter Reform I**. Sanctions become embargoes by the members that voted for them. Wars without a mandate carry an infamy surcharge. Agencies gain teeth (§5) |
| **Supranational** | 85–100 | 2.5 | Needs **Charter Reform II**. Sanctions become embargoes by every member. A mandate is effectively the only legitimate route to war. The UN levy is real. The ICC can indict leaders |

The **charter cap** clamps the target: 70 under the founding charter, 85 after Reform I, 100
after Reform II.
- **Reform I**, "Standing Mandate Force / Compulsory Jurisdiction", and **Reform II**,
  "Veto Restraint / UN Levy", are binding topics.
- They are vetoable, so the other permanent members must be won over or outlasted. This is
  where a hegemon spends decades.
- They need a two-thirds supermajority, like expulsion.
- They can be tabled only after authority has sat within 5 points of the current cap for 24
  months ("the organisation has outgrown its charter").

`E` is **one script value** read by every resolution's effects. It replaces the flat
modifiers with `multiplier = E`, and it gates each threshold change in form. Thresholds carry
hysteresis (enter at 70, leave at 66) so a UN hovering near a line does not flicker.

### 4.2 Membership benefits and burdens scale together

The membership modifier keeps scaling with authority, but it now brings its own costs (§7):
- dues, which grow with the tier;
- sovereignty friction with nationalist interest groups;
- exposure to binding decisions.

Non-member pariah status grows in steps: relations and prestige at Established; trade and
leverage at Strong; at Supranational, a standing sanctions case against any non-member of
major-power rank or above.

### 4.3 The floor: crisis and dissolution **(decided in outline; mechanics proposed)**

- **Crisis.** Below 10, a **UN crisis** situation opens, replacing `un_events.10`. It
  shows months to collapse at the current trend, and which great powers could save the UN
  by what action. It closes if authority climbs back above 20.
- **Dissolution.** At 0, **the UN dissolves**:
  - the HQ building is removed;
  - agencies and conventions lapse;
  - mandates are voided;
  - standing is frozen and hidden;
  - power blocs receive a one-time "vacuum" bonus.
  - A world-moment event goes to every former member.
- **Refounding (decided).** A new UN can be founded after a cooldown **(proposed: 20
  years)**.
  - The highest-prestige great power must not oppose the refounding. Opposing is an
    explicit choice at a founding conference, so the USA-and-the-League case is
    representable: the top power may stay out, but it must not block.
  - A refounded UN starts at low authority **(proposed: 25)** under the founding charter,
    with no reforms and no agencies.
  - The mechanics **(proposed)**: the founder tables a founding conference lasting 12
    months. The top power gets an event with the options *join*, *stay out* and *oppose*.
    *Oppose* ends the conference and restarts the cooldown at 10 years.

---

## 5. Resolutions with teeth

### 5.1 Punitive resolutions need grounds **(proposed; owner requirement: "votes must make sense and be transparent")**

Every country carries a **dossier**: a case-strength score (0–100) built from objective,
dated records, each decaying.
- infamy;
- wars declared without a mandate in the last ten years, weighted by the victim's power
  share;
- binding resolutions defied;
- mandates violated;
- sanctions busting;
- exposed severe covert operations (§7.4);
- nuclear use;
- breaches of conventions the country ratified (§5.3).

Each punitive topic has a minimum case strength before it can be tabled at all
**(proposed)**:

| Topic | Minimum case |
|---|---|
| condemn | 30 |
| sanctions | 50 |
| military mandate | 60 |
| ICC referral | 70, and a qualifying act |

The existing notoriety test (`un_mandate_target_is_notorious`) becomes a case threshold.

**A country with a clean record cannot be targeted.** The chamber shows every member its
own dossier ("Your exposure": which punitive topics could be tabled against you today, and
how the vote would likely go). That makes "sanctioned while the world likes me" impossible
by construction, and makes a real case visible before it lands.

### 5.2 Topic effects by tier **(proposed)**

| Topic | Contested (`E` 0.5) | Established (1.0) | Strong (1.5) | Supranational (2.5) |
|---|---|---|---|---|
| **condemn** | prestige and relations penalty | + infamy-decay penalty, mandate-eligible | + target cannot join defensive pacts | + members get a free defensive war goal against the condemned aggressor **(VERIFY IN-GAME: feasibility)** |
| **sanctions** | trade-advantage penalty × `E` | × `E`, plus influence | **embargo pacts** from every member that voted yes (`create_diplomatic_pact = { type = embargo }`, **VERIFY IN-GAME**) | embargo pacts from every member; busting is a covert op |
| **war without a mandate** | nothing | +infamy surcharge on war goals added (`on_wargoal_added`, the hook mandates already use) | surcharge × 2 | surcharge × 5; the AI avoids unmandated wars (strategy weight) |
| **mandate** | as today | as today | the mandate holder gets war support | the holder's war goal also cannot be contested by members |
| **peacekeeping** | observer mission | state mission (§9) | the mission state carries a war-goal infamy surcharge | a war goal against a mission state is prohibited for members **(VERIFY IN-GAME)** |

Costs fall on the enforcers too. An embargo is symmetric: the members who embargo lose the
trade as well. That is the free-rider tension in §7.2 made concrete.

### 5.3 Conventions become regimes with winners and losers **(proposed)**

Each convention stays a ratified global regime (the agency global plus the member modifier),
but its effect is multiplied by `E` and it names who pays.

| Convention | Winners | Losers / cost | Hook |
|---|---|---|---|
| **Climate (UNEP)** | vulnerable, low-emission states: less warming damage | high emitters: a binding `country_greenhouse_gas_emissions_mult` cut, paid in industrial output | Emissions read the **market leader's** modifier only (`gw_emission_multiplier_script_value`), so the accord must bind at market-leader level. It can also set `has_emissions_reduction_treaty`, which locks policy repeal |
| **NPT (IAEA)** | non-nuclear states get a security guarantee | nuclear-threshold states: inspections apply `country_nuclear_program_progress_mult` −(0.25 × `E`); at Supranational, a non-signatory proliferator is an automatic sanctions case | the nuclear system's modifier types; strike effects for the order pillar |
| **Law of the Sea (ITLOS)** | coastal and trading states: port connection cost, a merchant-marine throughput edge | naval powers lose freedom of action; **pirates**: vanilla `country_piracy_income_add` and `character_piracy_goods_capacity_mult` cut for members; piracy counts toward the dossier | vanilla piracy (`non_piracy_agreement` / `abandon_piracy` articles) |
| **Human rights (UNHRC)** | acceptance, as today, × `E` | members holding ethnostate, slavery or outlawed-dissent laws: standing and legitimacy pressure; authoritarian interest groups dislike it | law triggers; `ig_approval_effect` |
| **Decolonisation** | subjects: more liberty desire | colonial powers: `country_colonial_stability_drift_add` −× `E` | the colonial-empire system's modifier types |
| **Refugees (UNHCR)** | source states; hosts gain migration pull | hosts: turmoil and SoL strain in the receiving states | migration crowding |
| **Outer space (UNOOSA)** | laggards: shared progress | the leading space power: `building_orbital_battlestation` barred for members; colony claims registered, not sovereign | space-race globals |
| **Heritage (UNESCO)** | site states: tourism and cultural pull (`country_cultural_pull_add`) | site states: a construction penalty in protected states | tourism, cultural hegemony |
| **ICC** | small states get protection | members' leaders can be indicted for nuclear use, exposed regime-change operations or war crimes; the indicted ruler faces exile or removal **(VERIFY IN-GAME: which effect; `kill_character_audit` rules apply)** | covert exposure codes; nuclear strike effects |
| **Pandemic (WHO)** | — | — | **Deferred.** The mod has no pandemic system; keep it minor until one exists |

Treaty proposers no longer get their modifier up front. Everyone ratifies on passage.

---

## 6. Voting that makes sense, and says why

### 6.1 One itemised lean **(proposed)**

`un_vote_lean` is a script value per (voter, resolution), built as a sum of named terms.
Each term has a loc key, the way `un_secure_commitment_action`'s `ai.accept_score` already
itemises lobbying.

| Term | Rough weight |
|---|---|
| **grounds** (the target's case strength vs. the topic's threshold) | dominant |
| relations with the target | |
| relations with the proposer | |
| alliance / bloc / rivalry with either | |
| ideology distance to the target | |
| **cost to me** (for sanctions: my trade with the target; for a levy topic: my assessed share) | |
| **glass houses** (my own dossier is similar to the target's) | |
| the proposer's standing | |
| lobbying commitments | |
| topic-specific interests (colonial powers on decolonisation, emitters on climate, nuclear states on NPT) | |

### 6.2 The AI votes by the same lean **(proposed)**

AI members cast their ballot in script at day 30 (a hidden effect, not `un_vote.1`'s
`ai_chance`). The rule: yes if `lean + noise > 0`, a veto if the voter is a permanent member,
the lean is below the veto threshold and the topic is binding.

This does three things:
- The projection the chamber shows is the rule that decides, so they cannot drift.
- It sidesteps the unproven "named script value in `ai_chance`" question
  (`scripting_best_practices.md`).
- It keeps `un_vote.1` for human voters only.

### 6.3 What the chamber prints **(proposed)**

- **On the card:** grounds, as the dossier entries that support the case; the projected
  tally; and the top three reasons for each side, aggregated across voters ("Opposed:
  trade ties with the target (12 members); allied to the target (4)").
- **For a human voter:** their own lean with every term, so the popup explains the AI's
  view of their position.
- **For the target:** why each large member is voting as it is.

---

## 7. Real tradeoffs

### 7.1 Sovereignty: domestic politics **(proposed)**

From Strong upward, membership carries interest-group reactions scaled by tier, applied
through `ig_approval_effect`:
- **Resent it:** interest groups holding `ideology_patriotic`, `ideology_sovereignist`,
  `ideology_isolationist` or `ideology_jingoist`.
- **Welcome it:** those holding `ideology_humanitarian` or `ideology_pacifist`.
- **Leaving becomes a political demand.** The populist party ("anti-globalization") and
  `law_isolationism` make leaving a live issue, through an event when those interest groups
  are strong and authority is high.

### 7.2 Free riders: dues and the budget **(proposed)**

- **Assessed dues** are `GDP × rate(tier)`: 0 when Moribund, 0.1% when Contested, 0.2% when
  Established, 0.4% when Strong, and 1.0% when Supranational (the "UN levy"). They are
  applied as a country-scoped expense, charged where ROOT is the country.
- **Dues fund the budget, and the budget funds missions (§9).** A mission's strength scales
  with the budget it draws.
- **Withholding** is a journal-entry button. It saves the money, hurts the funding pillar in
  proportion to the withholder's assessment, and costs standing.
- **Article 19:** after 24 months in arrears, the member loses its General Assembly vote,
  as in the real Charter. The chamber shows "in arrears".
- **Programme contributors** (peacekeeping, development) pay on top of dues and are the
  ones credited with delivery. Everyone gets the stability; a few pay for it.

### 7.3 Situational losers

These are the convention losers in §5.3, plus the embargo symmetry in §5.2.

### 7.4 Spies **(proposed)**

- **HQ host:** its covert networks in every member grow faster (the delegations are in its
  capital).
- **Mission hosts:** hosting a peacekeeping or inspection mission lets each contributor's
  network in the host grow faster. Accepting help has a price, and the event that offers
  the mission says so.
- **Shared intelligence:** at Strong and above, members get a small
  `country_covert_defense_*_add`, following the `intelligence_sharing_pact` shield pattern.
- **Exposure is grounds:** an exposed severe operation (`covert_code_tier_severe`, at the
  `covert_warfare.1` choke point) is a dossier entry for the operator and a docket item for
  the victim (§8).

---

## 8. The docket: fewer events, driven by real situations

### 8.1 Replace the per-member random roll **(proposed)**

`un_events_on_action`'s monthly random roll for every member is removed.
- **The scan:** a global monthly pulse scans for situations and scores them by severity and
  by how much power is involved.
- **The pace:** it raises **at most one new docket item every three months**, which is about
  3–5 a year worldwide.
- **Who gets it:** each item goes to the countries actually involved (belligerents,
  neighbours, permanent members, donors with relations) and names the place.

| Situation | Source | Docket item |
|---|---|---|
| A war between members lasting 6+ months with heavy devastation | wars, state devastation | Security Council session: ceasefire resolution, peacekeeping mission, mandate, or mediation (a mediation success finally gives standing its missing source) |
| A state collapse | `je_state_collapse`, `failed_state_modifier` | stabilisation mission |
| Famine / devastation in specific states | `has_famine`, state devastation | donor appeal: an aid mission in those states |
| Nuclear test or strike | `nuclear_first_strike` / `_response_strike` / `_tactical_strike` | emergency session; an order-pillar entry; relief for states carrying `nuclear_strike_aftermath` |
| A warming threshold crossed (0.5 / 1 / 2 / 3 °C) | `temperature_anomaly_display` | climate summit with real emissions stakes |
| A severe covert operation exposed | `covert_warfare.1` | the victim's complaint: condemnation, or an ICC referral |
| A banking contagion wave / Great Depression | `great_depression_wave_*` | emergency lending facility, with conditions (the `debt_receivership` precedent) |
| An independence war / colonial collapse | the colonial-empire system, decolonisation events | trusteeship or decolonisation resolution |
| First space colony claimed | `sr_colony_*` | Outer Space Treaty |

### 8.2 Event rules **(proposed)**

- Every option costs something. The free "+1 authority" exits are removed.
- Events move pillars and standing, weighted by power share (§3.3), never authority
  directly.
- Flavour events for the countries involved (the host welcoming or resenting peacekeepers,
  the aid recipient) stay, and carry the §7.4 covert and §7.1 domestic consequences.

### 8.3 Player opportunity: proposal pacing **(owner requirement; mechanics proposed)**

- **Recess:** when a resolution closes, the floor is in recess for three months. Only human
  members may table during recess; AI proposal paths (scripted buttons and docket prompts)
  gate on `un_floor_open_to_ai`.
- **Docket prompts reach humans too.** A human who is party to a situation gets the same
  "you could table X" prompt the AI acts on, with the grounds attached.
- **Notice:** when the floor opens, human members get a notification
  **(VERIFY IN-GAME: custom message type vs. a lightweight event)**, and the chamber shows
  the recess countdown.
- **The victim goes first:** for a situation's own docket item, the aggrieved party gets
  first refusal for 30 days.

---

## 9. Missions: the UN happens in places **(proposed)**

- **The container:** a mission is a script container, in the mandate pattern
  (`un_mandate_effects.txt`).
  - Type: peacekeeping, aid, stabilisation, refugee camp, heritage site or inspection.
  - Host state(s) and host country.
  - Contributors list, budget share, months, progress, outcome.
  - A capped global registry.
- **State modifiers:** effects are state-scoped and refreshed from **`on_monthly_pulse_state`**
  (the CLAUDE.md rule for state-scoped scaling), with multipliers from the mission's budget
  and `E`.
  - Peacekeeping: turmoil −, devastation decay +.
  - Aid: SoL and food security +, mortality −.
  - Refugee camp: migration pull, turmoil.
  - Heritage: tourism + and construction −.
  - Inspection: the covert exposure in §7.4.
- **Outcomes:**
  - Peacekeeping succeeds after N months of peace with low turmoil. It fails if the host is
    attacked, the contributors withdraw, or the host expels the mission.
  - Aid succeeds when the state's SoL recovers above its threshold.
  - Outcomes feed the delivery and credibility pillars. Contributors get standing, as today.
- **Display:**
  - A **"UN Presence" tile** in the state panel, built with the existing library
    (`gui/te_state_panel_widgets.gui`, following the tourism card): mission type,
    contributors (flags), months, a progress bar, and effects with their breakdown.
  - A mission register in the chamber, beside the mandate register.
  - A **UN map mode** through the existing overlay (`te_apply_map_mode_overlay`): missions,
    or members by standing.
  - **Headlines** for world moments.

---

## 10. What happens to the existing subsystems

| Subsystem | Fate |
|---|---|
| **Military mandates** | Kept. At Strong and above, a mandate becomes the legitimate route to war (§5.2). Case eligibility reads the dossier (§5.1) instead of the notoriety trigger |
| **International standing** | Kept, and it stays separate from authority (the existing principle). Its sources gain mission delivery and mediation; its losses gain arrears. Standing is the per-country record, authority the institution's worth |
| **Lobbying** | Kept. Commitments become a term in the lean (§6.1). Opposition lobbying becomes possible once leans are itemised |
| **Chamber widget** | Kept, extended: grounds, projected vote with reasons, exposure, recess, docket, missions. The same scripted-GUI pattern |
| **Programme buttons** | Peacekeeping and development become mission contributions. Human rights and arms control become convention ratifications. The toggle-for-authority buttons are removed |
| **Champion / undermine** | Kept as the great-power stance feeding the commitment pillar |
| **Security Council / veto / expulsion** | Kept. A veto becomes a credibility entry weighted by the vetoer's power share. Charter reforms (§4.1) are binding and vetoable |
| **HQ** | Kept. Its host gets the covert growth in §7.4. It is removed on dissolution |

---

## 11. Saves **(decided: old saves must load; disbanding and refounding them is acceptable)**

- **Migration runs once**, on the first global pulse after the update, guarded by a
  migration-version global.
- **What carries over:** membership, seats, standing, mandates and ratified agencies.
  Authority is reseeded at the computed target, clamped to the charter cap.
- **What is dropped:** the removed programme modifiers go, through the existing
  `legacy_je_modifier_cleanup_effect` hook, and the old event cooldowns.
- **Fallback:** if a save's UN state cannot be reconciled, dissolve it with the world-moment
  event and waive the refounding cooldown for that one case.

---

## 12. Phasing **(decided: bug fixes, then this document, then implementation in this order)**

| Phase | Content | Why here |
|---|---|---|
| **1** | Power share; the pillars and target; approach; the two authority write helpers; every flat per-actor authority delta converted to a pillar entry; the credibility ledger; the display breakdown and history chart; the save migration | Everything else reads authority, so it must mean something first |
| **2** | Tiers and `E`; charter caps and the two reform topics; the crisis situation, dissolution and refounding | Makes the extremes real |
| **3** | Dossier and grounds; the itemised lean; AI voting in script; the chamber's reasons and exposure panel; recess and notifications | Must land **before** teeth (§5.2) get sharp, or high-tier sanctions will feel arbitrary (owner requirement) |
| **4** | The docket replacing the random roll; the event rewrite | Needs the lean and pillars to route consequences |
| **5** | Tradeoffs: dues and Article 19, interest-group sovereignty, covert hooks, convention regimes (§5.3), topic effects by tier (§5.2) | Needs `E`, grounds and the docket |
| **6** | Missions, the state tile, the map mode, delivery feeding the pillars | The largest new surface; everything it feeds exists by then |

Each phase ships a playable UN. Each is documented in a §0-style "as shipped" block at the top
of this file, as `monetary_policy_design.md` does.

---

## 13. Tuning constants **(all proposed)**

| Constant | Value | Section |
|---|---|---|
| `un_authority_approach_months` | 48 | §3.3 |
| `un_authority_max_step` | 1.0 / month | §3.3 |
| pillar ranges | see §3.2 | §3.2 |
| non-member stance (major power and above) | −0.5 | §3.2 |
| credibility entry decay | 15 years | §3.4 |
| tier boundaries | 20 / 45 / 70 / 85 | §4.1 |
| tier hysteresis | 4 points | §4.1 |
| charter caps | 70 / 85 / 100 | §4.1 |
| reform eligibility | within 5 of the cap for 24 months | §4.1 |
| `E` by tier | 0 / 0.5 / 1.0 / 1.5 / 2.5 | §4.1 |
| crisis threshold / exit | 10 / 20 | §4.3 |
| refounding cooldown / cooldown after an opposed conference / starting authority | 20 y / 10 y / 25 | §4.3 |
| case thresholds (condemn / sanctions / mandate / ICC) | 30 / 50 / 60 / 70 | §5.1 |
| dues by tier | 0 / 0.1% / 0.2% / 0.4% / 1.0% of GDP | §7.2 |
| arrears before losing the vote | 24 months | §7.2 |
| docket cadence | ≤ 1 new item per 3 months | §8.1 |
| recess | 3 months | §8.3 |
| victim's first refusal | 30 days | §8.3 |

---

## 14. Open questions for the owner

1. **Supranational war rule:** is "a mandate is effectively the only legitimate route to war"
   plus AI restraint right, or should the top tier stop short of changing AI war behaviour?
2. **Non-members in the commitment pillar:** count them at −0.5, or leave them to the
   participation pillar alone?
3. **ICC removal:** exile (the ruler is replaced, the character survives), or removal
   through `kill_character` with the audit's guards?
4. **The levy at Supranational:** is 1% of GDP the right order of magnitude?
5. **Pandemics:** keep the WHO topic minor until a pandemic system exists, or scope a small
   outbreak mechanic as part of phase 4's docket?
