# United Nations Redesign — Design

> **STATUS: PHASES 1 (THE AUTHORITY MODEL), 2 (THE LADDER, THE CEILING AND THE FLOOR) AND
> 3 (GROUNDS, THE ITEMISED LEAN, AI VOTING IN SCRIPT, THE RECESS) IMPLEMENTED.** Phase 1 has
> been play-tested; phases 2 and 3 are pending in-game verification. Phases 4–6 are designed
> but not built. Read [§0.3](#03-phase-3-as-shipped--rulings-deviations-and-open-checks),
> [§0.2](#02-phase-2-as-shipped--rulings-deviations-and-open-checks) and
> [§0.1](#01-phase-1-as-shipped--rulings-deviations-and-open-checks) before anything
> else if you are working on the code: they record where each phase deviates from the
> sections below. Written 2026-09-24 from a design
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

## 0.3 Phase 3 as shipped — rulings, deviations and open checks

Built 2026-09-25 on `claude/un-rework-continuation-8xn1se`, after phase 2. Not yet seen in a
running game. Implements §5.1 (the dossier and grounds), §6 (the itemised lean, AI voting in
script, what the chamber prints) and the recess of §8.3.

### Files

- `common/script_values/un_dossier_values.txt`: the dossier's tuning, `un_case_strength`, the
  grounds thresholds, and the lean: one script value per term (`un_lean_*`) and their sum,
  `un_vote_lean`.
- `common/scripted_triggers/un_dossier_triggers.txt`: `un_case_supports = { TOPIC }`, the
  recess tests (`un_floor_open_to_ai`, `un_may_table_now`) and the AI's veto rule
  (`un_vote_ai_should_veto`).
- `common/scripted_effects/un_dossier_effects.txt`: the only dossier writer
  (`un_dossier_record`), the monthly update (decay, the war-without-a-mandate detector, the
  recess clock), the lean snapshot, the AI ballot, the dispatchers and the reason tallies.
- **Events:** `un_vote.4` (hidden: one member's lean, and the AI's ballot) and `un_vote.5`
  (hidden: sends the AI its ballots thirty days after a resolution opens). `un_vote.1` now goes
  to human members only, and its AI weights are gone.
- **Record hooks:** `un_vote.3` option C, `un_events.5` option C, `un_events.8` option C,
  `un_mandate_on_violated`, `covert_warfare.1`'s immediate, and the three nuclear strike
  effects in `extra_effects.txt`.
- **Chamber:** the grounds on the card, "How the Assembly reads our position", why the
  members voted, each voter's lean in the ballot, a new "Our Exposure" section, and the
  recess line in the proposal section.

### Rulings: where phase 3 deviates from, or binds, the sections below

1. **The dossier's records.** Five decaying country variables, each capped at 60, with a
   five-year half-life (`un_dossier_decay_factor` 0.98851 a month), plus 0.8 × infamy up to
   50: `un_dos_aggression` (a war begun without a bound mandate: 10 + 100 × the world power
   share at war with the aggressor, at most 30; recorded once per war by a monthly detector
   on `is_diplomatic_play_initiator`), `un_dos_defiance` (a binding resolution refused +10,
   sanctions busted +8, the court defied +6), `un_dos_violation` (a mandate violated or
   abandoned +20), `un_dos_covert` (a severe operation exposed, when the exposure is not
   costless, +15), `un_dos_nuclear` (first strike +40, tactical +20, retaliation +10). Records
   are written only while a UN exists. **Breaches of ratified conventions** wait for the
   convention regimes of phase 5.
2. **Grounds.** Condemnation needs a case of 30, sanctions 50, a military mandate 60.
   The gates sit in the shared propose triggers and selectors, in `un_events.2`'s trigger
   and pick, and in `un_mandate_target_is_notorious`, whose old test (infamy 25 or already
   censured) is replaced by the mandate threshold. The ICC referral topic of the §5.1 table
   does not exist yet (the ICC topic founds the court); its threshold waits for it. The
   motion to strip a seat needs no dossier grounds: its case is the veto abuse its gate
   already requires.
3. **The lean** is the sum of ten named terms: the habit of consensus (+10), the grounds
   (half the target's case above or below the threshold, −20..+30), the target itself
   (−50, +20 at Strong or above), ties to the proposer (alliance +20, bloc +20, rivalry −30,
   relevance +5, relations ÷ 10), ties to the target (alliance −60, bloc −35, rivalry +30,
   relations ÷ −10), glass houses (−10 at a case of 30, −20 at 50), the proposer's standing
   (±2 / ±5), a pledge (+100), the target's acceptance (+15), the burden of an aid or
   peacekeeping request, and the member's interests on the topic.
4. **Porting the old weights.** Every per-topic `ai_chance` modifier moved into
   `un_lean_interests` or `un_lean_burden`. One that sat on the yes option alone keeps its
   size; one that sat on both options is ported as **half** the difference, because the old
   vote was proportional and a lean decides outright. The full difference would have made
   every great-power permanent member veto every ICC resolution.
5. **The AI's ballot.** `un_vote.5`, thirty days after a resolution opens, sends every AI
   member `un_vote.4`, which writes its lean and casts: a veto if it is a permanent member,
   the topic is binding, it pledged nothing and its lean is at or below −30 (−50 after a veto
   of its own, −10 at Moribund, where a veto costs nothing); otherwise yes when lean + noise
   > 0, the noise being one of −20 / −10 / 0 / +10 / +20. The monthly pulse sends the ballots
   two months in if `un_vote.5` did not fire. The ballot runs through the very
   `un_vote_cast_*` effects a human's vote does. The AI's target no longer accepts its own
   censure four times in five, as the old proportional weights made it do; it now almost
   never does.
6. **Human members** get `un_vote.1` as before, and see their own lean in the chamber from
   the day a resolution opens (`un_vote.4` is sent to them at opening and every month; it
   writes, it never casts).
7. **What the chamber prints (§6.3).** On the card: the target's case when the resolution
   was tabled against the topic's threshold, and its record now. Under the card: our own
   lean, term by term. In the ballot: every voter's lean, and a tally of the reasons that
   moved the members each way (a member counts once for every term of 10 or more in the
   direction it voted). **Deviation:** the design asked for the top three reasons each side;
   all are printed, which is simpler and as short in practice. **Deviation:** the exposure
   panel shows our record and which punitive topics it would support, but not "how the vote
   would likely go": that needs a hypothetical resolution to evaluate leans against, and was
   left out.
8. **The recess (§8.3).** When a resolution closes the floor is in recess for three months
   (`un_recess_months`). Every proposal path asks `un_may_table_now`: the propose triggers
   (so the AI's buttons and the chamber both) and every proposer event in the monthly roll.
   A human member may always table; the chamber tells it the floor is its own for now.
   Human members are notified when the floor opens. **Not built:** docket prompts reaching
   humans and the victim's first refusal, which belong to the docket (phase 4).

### Known roughnesses

- **The war detector sees one war at a time.** A country already recorded for a war it
  initiated is not recorded again for a second one begun before the first ends.
- **The words restate two numbers:** "−30 or below" and "give or take up to 20 points of
  chance" in `je_un_chamber_position_total`, and the thresholds in the exposure lines. Edit
  them with the script values.
- **Old saves:** a vote in session at the update is finished by the AI through the monthly
  fallback; un_vote.1 events already queued to AI members still fire, with the minimal
  weights left on the event, and count.

### IN-GAME VERIFICATION CHECKLIST (phase 3)

1. `scope:X = { add = sv }` inside a script value (`un_lean_grounds`) evaluates the script
   value in X's scope, as vanilla's `owner = { add = … }` does: a condemnation of a target
   with a heavy record shows a positive "case against the target" in our position.
2. `scope:un_vote_proposer.relations:root` inside a script value, evaluated in a hidden
   event whose ROOT is the voter, reads real relations.
3. A resolution opened by the AI: thirty days later every AI member has voted at once; the
   ballot shows each voter's lean; the reasons appear; our own position shows under the card.
4. `un_lean_tally_$LIST$` (a scripted-effect name built from a parameter) resolves: the
   reasons tally is non-empty after a vote.
5. A permanent member allied to a condemned target vetoes it; one merely rivalling the
   proposer does not.
6. After a vote closes, the proposal section shows the recess line for three months, the AI
   tables nothing in that time, and a notification says when the floor opens.
7. Starting a war against a great power without a mandate raises the aggressor's case by
   about 20 at the next monthly update ("Our Exposure").

---

## 0.2 Phase 2 as shipped — rulings, deviations and open checks

Built 2026-09-25 on `claude/un-rework-continuation-8xn1se`. Not yet seen in a running game.
Implements §4 (tiers, `E`, charter caps and reforms, the crisis, dissolution, refounding).

### Files

- `common/script_values/un_ladder_values.txt`: every phase-2 figure (tier floors and
  hysteresis, `E` by tier, charter ceilings, the reform clock, the crisis band and clock,
  founding values) and every derived value (`un_enforcement`, `un_charter_cap`,
  `un_tier_entry_value` / `_exit_value`, the crisis projections).
- `common/scripted_triggers/un_ladder_triggers.txt`: the tier tests
  (`un_tier_is_moribund`, `un_tier_at_least_contested` … `un_tier_is_supranational`, all
  numeric "at least" tests on `global_var:un_tier`), the charter tests, the crisis tests.
- `common/scripted_effects/un_ladder_effects.txt`: every writer of a phase-2 global (the
  table at its top), the monthly update, dissolution, the founding conference, and the
  shared `un_found_organisation` / `un_join_organisation` / `un_membership_end_effect`
  that the found, join and leave buttons now call.
- **Call sites changed:** `un_authority_monthly_update` (calls `un_ladder_monthly_update`
  after the step), `un_authority_target_value` (capped at `un_charter_cap`),
  `un_authority_step_value` (the collapse clock), `un_global_authority_on_action`
  (dissolution check last; bloc vacuum and conference every month), `je_united_nations`
  (tier status lines, crisis and dissolution lines, benefits and pariah re-keyed to tiers),
  `un_buttons.txt` (found / join / leave through the shared effects; a new charter-reform
  button), `un_vote_events.txt` (charter reform outcome and leans, `E` on condemnation and
  sanctions), `un_events.txt` (events 6, 10 reworked; 30–32 new; `E` on event 5),
  `un_vote_effects.txt` / `un_vote_cast_effects.txt` (supermajority, the free veto at
  Moribund), the chamber (op 6) and the authority widget (the ladder lines, the crisis
  panel).

### Rulings: where phase 2 deviates from, or binds, the sections below

1. **The tier is a stored global with hysteresis, capped by the charter.** `un_tier` (0–4)
   rises to the highest tier whose floor authority has reached and falls to the highest
   tier whose floor minus 4 it still holds. Both are capped at Established under the
   founding charter, Strong after Reform I. Only an old save can have authority above the
   ceiling; its tier is capped and its authority converges down.
2. **Where `E` applies (phase 2).** `multiplier = un_enforcement` on the Assembly's
   penalties: `un_condemned_modifier`, `un_non_binding_rebuke_modifier`,
   `un_sanctions_target_modifier`, `un_sanctions_voluntary_target_modifier` (un_vote.2), and
   the enforcers' bundles in `un_events.5` (`un_sanctions_enforcement_modifier`,
   `un_sanctions_partial_modifier`, `un_sanctions_busting_modifier`). **Not** applied to:
   `un_self_corrected_modifier` (the target's own act of contrition, at vote time), the
   conventions (§5.3 regimes are phase 5), membership benefits (still `authority / 50`,
   now paid from Contested up), `un_high_authority_infamy_modifier` (unchanged until the
   §5.2 mandate surcharge replaces it in phase 5), and NPT disarmament (still 80 / 75, which
   the ceiling now makes reachable only after Reform I). `un_enforcement` reads only
   globals, so the multiplier is sound in any scope; the loc prints it from the snapshot
   `un_enforcement_now` with `GetGlobalVariable`.
3. **Moribund.** A veto costs nothing: the credibility entry, the drain and isolation
   modifiers and the infamy are all waived; the proposer's anger (relations, catalyst)
   stays, because that is diplomacy, not the institution. Members receive no benefits.
   Every power bloc carries `un_bloc_vacuum_modifier` (+10 cohesion, +10% leverage
   generation), refreshed monthly by `un_ladder_bloc_vacuum_update`.
4. **Pariah steps (§4.2).** From Established a non-member carries
   `un_nonmember_pariah_modifier` (it was ≥ 60 / < 55); from Strong also
   `un_nonmember_pariah_strong_modifier` (−10% trade advantage, −10% leverage generation).
   The Supranational standing sanctions case waits for the dossier (phase 3).
5. **The charter reforms are the old `reform` topic.** It did nothing but book a
   credibility entry, so it was repurposed rather than duplicated. The resolution carries
   `un_res_charter_stage` (1 or 2, written by `un_charter_reform_open`), needs a two-thirds
   supermajority of all members (`un_resolution_needs_supermajority`, shared with
   expulsion; `un_vote_expulsion_passed` is renamed `un_vote_supermajority_passed`), and is
   flat-blocked by a veto as before. Tabling needs major-power rank and a ripe charter:
   24 consecutive months at or above `ceiling − 5` (a month below resets the count). Three
   paths share the gates: the chamber's Propose row (op 6), the new
   `un_propose_charter_reform_button` (the AI), and `un_events.6` (now "The Charter Has Been
   Outgrown", rolled only when ripe). Adoption is a credibility entry of +2 (reason 14) and
   raises the ceiling. **The reforms' own teeth** (embargoes, the mandate surcharge, the
   levy, veto restraint as a rule) are §5.2 / §7.2 material and wait for phase 5; for now
   a reform raises the ceiling and unlocks the tier.
6. **AI leans on a reform:** champions, human-rights champions and humanitarian-law
   countries +20; minor powers +10; isolationists and underminers −30; permanent members
   −20 (and +25 to vote against) on Reform II only. Veto: +30 against a non-permanent
   proposer (existing), +20 on Reform II, −80 for a champion of the order.
7. **The crisis replaces `un_events.10`'s roll.** It opens below 10 and closes above 20.
   When it opens, every great power, member or not, receives `un_events.10` once (stand by
   it at a cost in influence; join it; wait; let it fall for influence), and every other
   member a notification. The widget's crisis panel lists every great power that could lift
   the target and by how much (`un_crisis_rescue_gain`: 25 × its power share, for joining,
   championing, or ending its undermining).
8. **The collapse clock (deviation).** "At 0 the UN dissolves" cannot happen under the
   phase-1 approach: a step proportional to the gap approaches a target of 0 but never
   reaches it. So while the crisis is open **and the target itself is below 5**
   (`un_collapse_target_line`), the step is at most −0.25 a month. A UN the world has given
   up on then reaches 0 in at most forty months from 10; one whose target is 5 or more
   lingers in crisis instead. Dissolution fires at authority 0 during a crisis, checked
   last in the global pulse so the month's upkeep runs against a UN that still exists.
9. **Dissolution (§4.3) as designed,** with these choices: the resolution history and the
   mandate register are kept as the record; the ledger log is destroyed; sanctions regimes
   lapse on both sides; timed condemnations run out on their own; standing is frozen (the
   variable stays, the tier modifiers go); `un_charter_signed` is cleared so the charter
   event can fire again. Power blocs receive `un_dissolution_vacuum_modifier` (+20
   cohesion, +20% leverage generation, ten years, decaying).
10. **Refounding.** After a dissolution the found button convenes a founding conference
    (`un_conference_open`) once the 20-year cooldown has run. The world's leading power —
    the highest-prestige great power, unless that is the convener — receives
    `un_events.31` (join / stay out / oppose). Opposing wrecks the conference, restarts the
    cooldown at ten years and tells the convener (`un_events.32`). Otherwise, twelve months
    on, the UN is refounded at 25 under the founding charter with no agencies, the
    convener as founder, the leading power as a member if it chose to join, and a fresh
    five-year founding window for permanent seats. A convener that stops existing ends the
    conference without a new cooldown.
11. **Bug fix found on the way:** `un_propose_expulsion_button` was defined but never
    registered on `je_united_nations`, so the AI could never move to strip a permanent seat.
    It is registered now.
12. **Old saves:** the charter starts at level 0 and the tier is computed on the first
    monthly update. A save whose authority is above 70 keeps it and converges down to the
    ceiling.

### Known roughnesses

- **A lingering crisis can last for ever** if the target settles between 5 and 10; that is
  intended (the organisation limps on), but nothing ends it except the world changing.
- **An empty UN never dissolves.** With no members its target is about 10, so it hovers at
  the crisis line. Not reachable in ordinary play (the founder would have to leave too).
- **The pariah and benefits changes move thresholds** in existing games: pariah status now
  starts at 45 rather than 60, and benefits at 20 (Contested) rather than 30.
- **Whether a stored `multiplier` re-reads `E` live** is unverified. If it does, a
  sanctions regime strengthens and weakens with the tier; if not, it keeps the `E` of the
  month it was imposed. Either reading is acceptable.

### IN-GAME VERIFICATION CHECKLIST (phase 2)

1. After one month in a game with a founded UN: the journal entry shows a tier line; the
   widget shows the tier, the charter and the reform clock; `debug.log` has no "used but
   never set" for `un_tier`, `un_enforcement_now`, `un_charter_level` or
   `un_charter_pressure_months`.
2. `[GetGlobalVariable('un_enforcement_now').GetValue|1]` renders in the condemnation and
   sanctions tooltips (vote popup and chamber card).
3. A condemnation carried at Contested gives the target half the modifier's values.
4. `event te_debug_un.1` → *Put the next charter reform on the table*: the chamber's
   Charter Reform row enables; table it; the card names "Charter Reform I" and the
   supermajority rule; carried un-vetoed, the widget shows the ceiling at 85. A permanent
   member's veto blocks it outright.
5. A veto cast at Moribund shows the Moribund tooltip and books no ledger entry.
6. *Doom the UN*: at the next monthly update the crisis opens (great powers get
   `un_events.10`, other members a notification, the widget its crisis panel); authority
   falls a quarter point a month; at 0 the UN dissolves: `un_events.30` to every member and
   great power, the headquarters demolished, agencies gone, mandates void, both vacuum
   modifiers on every power bloc (`power_bloc ?= { add_modifier }` from country scope, as
   `te_unused_mandate_reserve_on_action` does), and the Found button greyed with the
   cooldown tooltip.
7. *Skip the refounding cooldown*, then Found: a conference opens and the leading power gets
   `un_events.31`. Opposing sends `un_events.32` to the convener and restores a ten-year
   cooldown. Otherwise, skipping again ends the conference's year: at the next monthly
   update the UN is refounded at 25, and the charter event goes out again.
8. The AI tables charter reforms and expulsion motions through the journal-entry buttons.

---

## 0.1 Phase 1 as shipped — rulings, deviations and open checks

Built 2026-09-24 on `claude/un-system-redesign-8t6kim` (PR #411) and play-tested: the
pillars, the ledger log and the nuclear hooks work in game.

### Files

- `common/script_values/un_authority_values.txt`: every figure and every pillar formula.
- `common/scripted_effects/un_authority_effects.txt`: the monthly update and every writer.
  The reason-code table is at its top.
- `common/scripted_effects/un_authority_display_effects.txt` and
  `common/scripted_guis/un_authority_sguis.txt`: the read-only display.
- `gui/journal_entry_widgets/un_authority_widget.gui`: the **Why UN Authority Is Moving**
  widget, in container 3.
- **Call sites converted:** `events/un_events.txt`, `events/un_vote_events.txt`,
  `common/scripted_effects/un_vote_effects.txt` (veto), `un_mandate_effects.txt` (the two
  hooks), `common/scripted_buttons/un_buttons.txt` (lift sanctions; the programme toggles;
  the permanent-member walkout), and `extra_effects.txt` (the three nuclear strike effects).
- **Supporting changes:** `gen_un_button_descs.py` learned to describe
  `un_ledger_actor_entry`. The old drift script values in `un_script_values.txt` are gone.

### Rulings: where phase 1 deviates from, or binds, the sections below

1. **Funding is a proxy until dues exist (phase 5).** It is the power-weighted share of
   major-and-above members running UN programmes (two programmes count in full), mapped to
   −5..+10, not the §3.2 −10..+10. Programmes feed **funding only**, never commitment, so no
   fact is counted twice. Commitment is stance (champion ±1, bloc alignment) × power share.
2. **Order.** The war half is `−40 × the share of world power at war with a fellow member`,
   floored at −15. The ledger half holds nuclear use only:
   - first strike: order −4 plus a direct shock of −3;
   - tactical strike: −1.5;
   - retaliation: −2;
   - all unweighted, because nuclear use is grave whoever does it.

   "Aggression without a mandate" waits for the dossier (phase 3).
3. **Delivery is a ledger until missions exist (phase 6).** It is fed by aid and peacekeepers
   delivered (`un_events.4` and `7`, options A/B), aid and peacekeeping resolutions carried,
   and mandates discharged.
4. **No charter cap yet.** The target is clamped to 0..100. The 70 / 85 / 100 caps arrive
   with the reform topics in phase 2, so phase 1 alone cannot make the NPT-at-80 rule
   unreachable. *(Superseded by phase 2, §0.2.)*
5. **Ledgers decay with a four-year half-life** (`un_ledger_decay_factor` 0.9857 a month),
   not the fifteen-year entry life of §3.4. At the event rates surveyed in §1.1, the
   credibility and delivery stocks settle around +7 each in a quiet world, rather than
   saturating their caps.
6. **Conversions.** Every flat authority delta became a ledger entry:
   - **Event options:** half the old points, weighted by the actor. Aid and peacekeeping
     *delivered* go to delivery; everything else goes to credibility.
   - **Resolution outcomes:** unweighted "institutional" entries:
     - carried +1, or +1.5 for the treaties that found an agency;
     - carried in weaker form after a veto +0.5;
     - fell −1;
     - expulsion carried +1, expulsion fell −1;
     - aid and peacekeeping carried go to delivery.
   - **Veto:** −1.5 × the vetoer's weight, **every** veto, not only the first.
   - **Mandates:** discharged is delivery +2 × weight; violated is credibility −3 × weight.
   - **Lifting sanctions:** credibility −1 × weight.
   - **Programme toggles:** their ±2–3 authority is simply gone. A programme counts toward
     funding for exactly as long as it runs.
7. **World moments shipped:**
   - **A permanent member leaving** through the Leave button costs −4 × the leaver's weight,
     capped at ×2 (`un_shock_weight`). That is −4 for a typical great power, up to −8 for
     a superpower, and about −1 for a faded power still holding its seat. The owner asked
     for the weighting on 2026-09-25. A member absorbed by a merger or annexation never
     passes through the button, so it causes no shock.
   - **A nuclear first strike** costs −3, unweighted.
   - Both are logged.
8. **Old saves keep their authority** (§11 said reseed at the target). Their ledgers start
   empty, so the first target understates an established UN, and a reseed would have
   dropped authority by around twenty points in one month. They converge at the ordinary
   pace instead; `un_model_version` marks the conversion.
9. **Founding** still sets 50. A new UN therefore sinks toward roughly 30 until its programmes
   and ledgers fill: the young UN is weak.
10. **The per-member random events are unchanged** apart from their authority deltas.
    Replacing them is phase 4.

### Known roughnesses

- **The log records only sizeable entries.** It keeps the 12 most recent entries of at
  least 0.05 after weighting, so micro-states' gestures never appear. That is intended, but
  it means the log is not a complete record.
- **Displayed weights can drift slightly.** The event tooltips print the actor's weight from
  `var:un_power_share`, which is refreshed monthly, so a tooltip can differ in the second
  decimal from the weight applied on the day.
- **New countries have no weight yet.** A country created mid-month has no power share
  until the next update, so its acts weigh 0 for that month.

### IN-GAME VERIFICATION CHECKLIST (phase 1)

1. After one month in a game with a founded UN:
   - the widget shows a target and seven pillar values;
   - the JE status line reads "Moving toward …";
   - `debug.log` has no "used but never set" for `un_power_share`, `un_ledger_*`,
     `un_led_stage` or `un_pillar_*`.
2. `change_global_variable = { … multiply = … }` works on a global. The three ledgers should
   visibly shrink month to month with no new entries.
3. `set_global_variable` with an inline `value = { value = un_actor_weight multiply = N }`
   produces a non-zero entry: take a great-power option in any UN event and check the
   log.
4. `always = $WEIGHTED$` / `$WITH_ACTOR$` parameters select the right branch: an
   institutional entry logs "the General Assembly", an actor entry logs the country.
5. The event tooltips render
   `[ROOT.GetCountry.MakeScope.ScriptValue('un_actor_weight')|2]` as a number.
6. The powers list shows champions, underminers and outsiders, each with its share. An
   annexed actor in the log reads "a former member".
7. The history chart draws both series once a month has been sampled.
8. A nuclear first strike drops the order pillar and logs both entries. A permanent member
   leaving logs −4 × its weight (at most ×2).
9. There is no noticeable hitch on the first of the month: about seven `every_country`
   sweeps run once a month from the global pulse.

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
| **Base** | 15 | constant |
| **Participation** | 0 … +25 | `25 × Σ power_share` of members |
| **Great-power commitment** | −25 … +25 | `25 × Σ stance × power_share` over **members only**. Stance: champion **+1**, neutral **0**, undermine **−1**. A member's stance also gains `country_un_institutional_alignment` (the Multilateral Institutions bloc principle), so that hook survives |
| **Credibility** | −15 … +15 | a rolling record of binding decisions enforced vs. defied, vetoed or ignored (§3.4) |
| **Funding** | −10 … +10 | the share of assessed dues actually paid, weighted by the size of each assessment (§7.2) |
| **Peace & order** | −20 … 0 | wars between members weighted by power share (the existing `un_member_wars_weight` shape, made power-weighted); aggression without a mandate; nuclear use. Each decays |
| **Delivery** | 0 … +10 | missions concluded successfully in the last ten years, minus failed ones, weighted by mission size (§9) |

**Non-members count only against participation (decided 2026-09-24).** Participation says
who is in; commitment says what the members do. A great power outside the UN therefore shows
up once in the breakdown, not twice. Obstructing from inside and walking out also stay
distinct choices:
- An obstructing member keeps its veto and its voice, drains commitment, and pays standing.
- A leaver loses its seat and its benefits, and drains participation.

What a hostile outsider does is still charged to it, through the other pillars: wars without
a mandate go to order, defiance goes to credibility.

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

Terms are in pillar order: base, participation, commitment, credibility, funding, order,
delivery.

**A normal multipolar world.** 90% of power in the UN, stances mostly neutral, dues paid,
some small wars, a few missions.
`15 + 22.5 + 0 + 0 + 10 − 5 + 3 ≈ 46`.

**A sole superpower, all in.** 40% of world power; member, championing, paying,
enforcing; two allies championing; 95% of power inside.
- `15 + 23.75 + 12.5 + 10 + 10 − 2 + 8 ≈ 77`.
- That is capped at 70 until the first charter reform (§4.1).
- To pass 90 it also needs both reforms, the other great powers eventually championing,
  and full credibility and delivery.
- That is decades of work, and other permanent members can veto the reforms along the way.

**The same superpower, all out.** It has left, and wages wars without mandates. Some members
it still leads are undermining from inside. 55% of power remains in the UN.
- `15 + 13.75 − 2.5 − 10 + 2 − 10 + 0 ≈ 8`.
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
| **war without a mandate** | nothing | +infamy surcharge on war goals added (`on_wargoal_added`, the hook mandates already use) | surcharge × 2 | surcharge × 5. The surcharge is the requirement: the AI already weighs infamy before adding goals or starting wars. An AI strategy weight against wars without a mandate is a **nice-to-have (decided 2026-09-24)** |
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
| **ICC** | small states get protection | members' leaders can be indicted for nuclear use, exposed regime-change operations or war crimes. **An indicted ruler is exiled (decided 2026-09-24)** with the vanilla `exile_character` effect, which sends the character to the exile pool. **VERIFY IN-GAME** that exiling a ruler installs the heir cleanly under every government type | covert exposure codes; nuclear strike effects |
| **Pandemic (WHO)** | members coordinate: faster containment | members accept restrictions (lockdown costs) | **Nice-to-have (decided 2026-09-24).** Hook into vanilla's Spanish Flu, not a new system: `je_spanish_flu`, `plague_modifier` on states, the `plague_lockdown` / `plague_measures` country variables, the `spanish_flu_response` decision and the `plague.*` events. For example, WHO members advance `plague_restrictions_tracker` faster. Until then, keep the topic minor |

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
  Established, 0.4% when Strong, and 1.0% when Supranational (the "UN levy"; **the 1% was
  decided 2026-09-24**). They are applied as a country-scoped expense, charged where ROOT is
  the country.
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
| *(nice-to-have)* Vanilla Spanish Flu spreading across countries | states carrying `plague_modifier` | WHO coordination (§5.3) |

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
  Authority is kept and converges on the target at the ordinary pace (as shipped in phase
  1, §0.1 ruling 8; the first draft reseeded it at the target).
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
| pillar ranges (base 15, participation 0–25, …) | see §3.2 | §3.2 |
| ledger decay (credibility, delivery, order) | 4-year half-life, ×0.9857 a month (phase 1; §0.1 ruling 5) | §3.4 |
| actor weight: reference share / cap | 0.10 of world prestige = ×1 / ×5 | §3.1 |
| funding proxy until dues | −5 + 15 × programme ratio (§0.1 ruling 1) | §3.2 |
| tier boundaries | 20 / 45 / 70 / 85 | §4.1 |
| tier hysteresis | 4 points | §4.1 |
| charter caps | 70 / 85 / 100 | §4.1 |
| reform eligibility | within 5 of the cap for 24 months | §4.1 |
| `E` by tier | 0 / 0.5 / 1.0 / 1.5 / 2.5 | §4.1 |
| crisis threshold / exit | 10 / 20 | §4.3 |
| collapse line / minimum fall while the clock runs | target < 5 / 0.25 a month (phase 2; §0.2 ruling 8) | §4.3 |
| bloc vacuum (Moribund or dissolved) / at dissolution | +10 cohesion, +10% leverage / +20, +20% for 10 years | §4.1, §4.3 |
| pariah steps | Established: relations and prestige; Strong: also −10% trade advantage and leverage | §4.2 |
| refounding cooldown / cooldown after an opposed conference / starting authority | 20 y / 10 y / 25 | §4.3 |
| case thresholds (condemn / sanctions / mandate / ICC) | 30 / 50 / 60 / 70 | §5.1 |
| dues by tier | 0 / 0.1% / 0.2% / 0.4% / 1.0% of GDP (the 1.0% is decided) | §7.2 |
| arrears before losing the vote | 24 months | §7.2 |
| dossier: half-life / record cap / infamy weight and cap | 5 years / 60 / 0.8 up to 50 (phase 3; §0.3 ruling 1) | §5.1 |
| dossier points: aggression / defiance / busting / court / violation / covert / first strike / tactical / retaliation | 10 + 100 × share, max 30 / 10 / 8 / 6 / 20 / 15 / 40 / 20 / 10 | §5.1 |
| lean: consensus / veto line (recent veto, Moribund) / noise / reason size | +10 / −30 (−50, −10) / ±20 in steps of 10 / 10 | §6.2 |
| docket cadence | ≤ 1 new item per 3 months | §8.1 |
| recess | 3 months | §8.3 |
| victim's first refusal | 30 days | §8.3 |

---

## 14. Owner decisions, 2026-09-24

The five questions left open by the first draft, as answered:

1. **Supranational war rule:** the infamy surcharge is the requirement. The AI already
   weighs infamy before adding war goals or starting wars. An explicit AI strategy weight
   against wars without a mandate is a nice-to-have (§5.2).
2. **Non-members:** they count only against participation, not commitment. This was Claude's
   recommendation; the owner was indifferent. The base and participation were rebalanced to
   15 and 0–25 so the §3.5 examples hold (§3.2).
3. **ICC:** an indicted ruler is exiled, not killed (§5.3).
4. **The levy at Supranational:** 1% of GDP (§7.2).
5. **Pandemics:** a nice-to-have. If built, the WHO hooks vanilla's Spanish Flu rather than a
   new outbreak system (§5.3, §8.1).
