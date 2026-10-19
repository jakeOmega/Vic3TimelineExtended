# Covert Warfare: watching caught operations, domestic backlash, Counterintelligence Support

Design agreed with the owner on 2026-10-16. Branch `feat/covert-counterintel-backlash`
(worktree `~/src/vic3te-covert-ci`). Read `docs/systems/mod_systems.md` § Covert Warfare
System before planning; this document assumes it.

## Intent

Covert Warfare today treats a catch as a single moment: the detection roll burns the
operation, the attacker picks Acknowledge or Deny, the defender picks a response, done.
Three gaps follow from that:

1. **A defender can't play a caught operation back.** Real services often leave a blown
   operation running to learn the other service. The owner wants the defender to be able
   to keep quiet, let the operation run, and grow their own network inside the attacker
   while it does.
2. **Spying has no politics at home.** Being caught spying on a friend costs infamy and
   relations abroad, but nobody at home cares, and a public exposure of a foreign operation
   doesn't move domestic opinion against the country behind it.
3. **Covert work is all offence.** There is no way to spend your own service protecting an
   ally.

The current relations block (some operations can't target countries we're on good terms
with) is replaced by consequences: you may spy on a friend, and pay for it at home and
abroad if caught.

The fourth request, whether pacts or treaty articles can be hidden from third parties, is
research only. Its findings are in § D; nothing is built from it in this branch.

## Goals

- A caught operation can be left running. The attacker isn't told. The defender's network
  inside the attacker grows while it runs, and the defender can expose it at any time from a
  new **Known Foreign Operations** section of the Covert Warfare panel.
- Spying on a friend has domestic costs for the attacker if caught; an exposed foreign
  operation turns the defender's public against the attacker and its friends at home.
- A new defensive operation, **Counterintelligence Support**, raises a friend's covert
  defences.
- One definition of "friend", used everywhere these features need one.
- AI and players run under the same rules (house rule: asymmetric outcomes come from shared
  mechanics, not `is_ai` branches), with the AI's watch/expose choices stochastic.

## Non-goals

- Hiding pacts or treaty articles from third parties (research only, § D).
- Changing what a watched operation does to the defender. It keeps hurting at full strength;
  that is the price of watching (owner, explicit).
- Giving the protector anything from Counterintelligence Support: no network inside the
  ally, no Tradecraft, no head start (owner, explicit).
- Telling the attacker its operation is being watched. There is no "the attacker notices"
  mechanic.
- Rebalancing detection, networks, Tradecraft or exposure costs beyond what is named here.

## Anti-goals (would make this a failure even if it technically works)

- AI countries suddenly spying on their friends because the `possible` block came off.
- Counterintelligence Support quietly planting a network inside the ally (the existing
  network machinery does this for every operation target unless excluded, see § C).
- A watched operation being caught again and again (it's already known), or a defender
  missing a catch because a cooldown swallowed the decision.
- A Known Foreign Operations row pointing at an operation that has ended.

## The definition of a friend

One scripted trigger, country scope, `$TARGET$` argument, e.g. `covert_is_friend`:

- relations ≥ `relations_threshold:cordial` (20) **and** a tie: alliance or defensive pact,
  the same power bloc (guard with `is_in_power_bloc = yes` as
  `covert_exposure_third_party_blowback` does, so two blocless countries don't match), or
  either one the other's overlord/subject; **or**
- relations ≥ `relations_threshold:amicable` (50) with no tie.

Owner: ties never count on their own; good relations are always required (the
Australia/New Zealand example: two members of one bloc who dislike each other are not
friends). The thresholds above are my call. Relations are symmetric, so the trigger
answers the same both ways.

Consumers: the attacker's backlash (§ B), the defender's backlash scaling (§ B),
Counterintelligence Support's `possible` and `requirement_to_maintain` (§ C), and the AI's
launch checks (§ B, "Relations block removed").

## A. Watching a caught operation

### Flow

Today `covert_ops_roll_detection_all` (operator's monthly pulse) picks one caught operation
and fires `covert_warfare.1` on the **attacker**; `.1`'s `after` burns it and fires
`covert_warfare.2` on the defender. The new flow puts the defender's decision first:

1. The roll skips operations already known to their target, and operations with a decision
   pending (`every_in_list` takes a `limit`).
2. When an operation is caught:
   - **Defender has a covert service** (`je_covert_warfare` active): the defender decides
     whether to expose or watch.
     - Player defender: a new event on the defender (next free id in the
       `covert_warfare` namespace) with the caught operation in scope. Two options:
       **Expose them** (default) and **Let it run**. It does not sit behind `.2`'s 24-month
       `iw_defender_event_cooldown`.
     - AI defender: resolved in script at roll time, without the event (§ AI below).
   - **Defender has no covert service**: today's flow, unchanged (straight to `.1`). My
     call: no decision popup that offers only one live option; the service is what makes
     watching possible, and the defender has no network machinery without it (the same rule
     `.2`'s "retaliate in kind" option already applies).
3. **Expose** (from the event, the AI branch, or the panel button later) runs today's flow:
   `.1` fires on the attacker with the operation saved as `scope:iw_burned_op`, the
   attacker picks Acknowledge or Deny, `.1`'s `after` burns it and fires `.2` on the
   defender as today. The exposure costs are computed from the operation's phase **at the
   time of exposure**, so an operation watched into its fully operational phase pays the
   ×1.5 phase factor. That is intended: a long-watched operation is a worse scandal.
4. **Let it run**: the operation is marked as known to its target and recorded on the
   defender (data model below). A network for the defender inside the attacker is created
   if there is none (the `covert_retaliation_seed_network` shape, without the seed amount).
   The attacker sees nothing.

`.1`'s `immediate` exists because the container can die before a click (stand-down, the
monthly sync, a lapsed pact). The new defender event has the same problem over its
`duration`: read the operation in `immediate`, guard every later use with `exists`, and
let Expose do nothing (with a line saying so) if the operation has ended meanwhile.

### Data model

Operation containers belong to the operator (parent, `iw_ops` list) and carry no operator
variable; the header rule is never to read `parent`. My call for the defender's side:

- **On the operation container:** a flag (e.g. `iw_known`) set on Let it run. The detection
  roll reads it; the attacker's own panel never shows it. A pending-decision flag covers
  the event's open days.
- **On the defender:** a record container per watched operation, parented to the defender,
  listed in a defender variable list (e.g. `iw_known_ops`). It holds the attacker country,
  the attacker's capital state (the row names the attacker through the capital-state chain,
  `gui_modding_guide.md` gotcha 15), the operation's type code, and the date or month it was
  caught. Record by (attacker, type code), not by a reference to the foreign container: the
  no-duplicate rule makes (type, target) unique per operator, so the live operation is
  `any_in_list = { variable = iw_ops var:iw_target ?= <defender> var:iw_type_code = <code> has_variable = iw_known }`
  on the attacker. That avoids holding references to containers another country destroys.
  A relaunch of the same type has no `iw_known` flag, so the old record doesn't adopt it.
- **Reaping:** wherever the attacker's container is destroyed (`covert_op_destroy`, and
  the direct reap in `covert_op_sync`), the defender's record for it goes too, so no row
  outlives its operation by a month. The defender's monthly pulse is the backstop: it
  destroys records whose operation no longer exists or whose attacker is gone
  (`remove_list_variable` before `destroy_container`, as `iw_ops` does). Old saves: every
  read of the new list behind `has_variable_list`.
- **One exposure in flight per attacker.** `.1` keeps the burned operation's state on the
  attacker itself (`iw_burned_type_code` and its siblings; its own comment says two open
  instances would overwrite each other). The new flow makes that reachable: a roll, a
  defender's decision, several Expose clicks and the AI's monthly expose rolls can all land
  inside `.1`'s three days. My call: a lockout. While a `.1` is open on an attacker, Expose
  on that attacker's operations is greyed with a reason, and roll or AI exposures wait for
  the next month. Reworking `.1` to carry per-instance state is the alternative, and much
  larger.

### Network growth

`covert_nets_sync` step 2 counts only the operator's own operations per network. Watched
operations must also count toward the defender's network inside the attacker: each month,
each watched operation grows that network as an operation of the defender's own would,
weighted by the watched operation's priority (a busier operation shows more of the
attacker's service). Starting figures, my call: 4 points a month at priority 1, × the
existing priority effect multipliers (1.35, 1.6), through `covert_net_gain` so the
diminishing return above half strength applies. The Tradecraft (and UN host) multipliers
live in `covert_net_tick_gain`, not `covert_net_gain`, so the watch gain goes through the
tick or applies them itself. Compare: an
operation of one's own grows its network by 2 a month (`covert_net_gain_base`), and the
"retaliate in kind" seed is 25 once. A watched network should outgrow exposing and
retaliating within about six months, because watching costs the defender the operation's
continued harm.

A watched operation also stops that network decaying, as an operation of one's own does.
Growth runs only on the defender's journal-entry pulse (networks have no other clock); a
defender who loses the entry keeps its records but stops growing.

### Known Foreign Operations panel section

A new section in `widget_je_covert_status`, placed with Counterintelligence (beside or
inside it is the builder's layout call, following `docs/guides/gui_style_guide.md`):

- Hidden while the defender watches nothing.
- One row per record: the attacker's flag and name, the operation's type (its diplomatic
  action icon and name, as the Operations rows draw them), how long it has been watched,
  and, on hover, what watching is earning (the network's strength inside the attacker)
  and what the operation is still costing us (its type's effect on its target).
- An **Expose** button per row. Hover says what exposure will do: the attacker pays the
  exposure costs, our public turns on them (§ B), and the network gain stops.
- The Military panel's Covert tab instances the same sections (`gui/panel_military.gui`);
  the new section must work there too, as the existing ones do.

The button passes the row's record container to a scripted GUI as a saved scope. That is
the same link as the priority stepper's `AddScope('iw_op', ScriptContainer.MakeScope)`,
which has no vanilla precedent and no recorded play-test. Build it fail-closed
(`is_valid` checks the scope exists, is tagged as a record, and is in the viewer's own
list), and do the exposure in a hidden event the click orders, not in the scripted GUI
effect itself (the trophies pattern, `monument_trophy_events.10`–`.13`), because the
engine walks scripted-GUI effects to render tooltips. Named contingency if the link fails
in game: Expose opens an event listing the watched operations as options.

### AI

Same choices, chosen by chance (owner: "a bit more stochastic … with a chance of exposing
early"). Starting figures, my call, to tune in play:

- At the catch: watch with 60% chance for mild, moderate and war-tier operations, 15% for
  severe ones; +20 points if the attacker is a friend (watching avoids a public row);
  10% flat if the network inside the attacker is already at 75 or more (nothing left to
  learn).
- Each month, per watched operation: expose with 2% + 0.1% per point of network strength
  inside the attacker; 25% a month once the network is at 75 or more; +5 points for a
  severe operation.

## B. Domestic backlash

### Attacker caught spying on a friend

Evaluated in `.1`'s `immediate` and copied onto the operator beside `iw_burned_type_code`
(the options run days later and `change_relations` lands then; same reason as the
existing copies). Nothing happens if the target wasn't a friend, or if the exposure is
costless (`covert_exposure_is_costless`, a war-tier operation caught at war).

- **At home:**
  - The lobby that favours the target loses appeasement: `lobby_pro_country` with that
    target, or `lobby_pro_overlord` when the target is our overlord
    (`every_political_lobby` + `is_political_lobby_type` + `target`, as
    `nd_lobby_react` does). Amounts by tier: mild −3, moderate −5, severe −8 (war tier
    caught in the run-up to war counts as severe). Owner's yardstick: about 5, a moderate
    to strong vanilla lobby event; vanilla's most common negative event amount is −5. The
    lobby's interest groups lose approval through the lobby itself; no separate IG approval
    hit (owner).
  - Legitimacy falls: a decaying country modifier, `country_legitimacy_base_add`, about
    −3 / −5 / −8 by tier, for `short_modifier_time` (2.5 years). Proportions are my call.
  - **Acknowledge pays the full amount at home; Deny pays half** (owner).
  - With no such lobby, the legitimacy hit still lands and the appeasement line does
    nothing. Say so in the option tooltip rather than printing a lobby that isn't there.
- **Abroad:** the existing infamy and relations costs, with the relations hit ×1.5 when the
  target was a friend (my call; a betrayal). Deny already pays more relations than
  Acknowledge, which matches "Deny costs less at home, more abroad" (owner).
- **Constants, not variable multipliers.** `add_modifier`'s `multiplier` is re-evaluated
  against ROOT on later ticks (see the priority section of `mod_systems.md`), and
  `iw_burned_type_code` is removed in `after`, so a multiplier that reads it would fall to
  zero. Branch by tier onto literal values or constant script values.
- Appeasement factor: a mod-defined factor in a new
  `common/political_lobby_appeasement/` file (e.g. "Caught spying on [target]") gives the
  lobby tooltip a named line; `appeasement_special_events_negative` is the fallback if a
  mod factor proves unusable. Builder's call after checking.

### A foreign operation exposed at home (the defender's side)

Owner: the public turns on the foreign country and on those at home who are friendly to it.

- On every exposure (whether the defender chose it, the panel button did, or the defender
  had no service and today's flow ran): the interest groups in the defender's pro-attacker
  lobby (`lobby_pro_country` targeting the attacker, or `lobby_pro_overlord` if the
  attacker is the overlord) take a decaying `interest_group_pol_str_mult` modifier, about
  −5% / −10% / −15% by tier, ×1.5 when the attacker was a friend, for
  `short_modifier_time`. My calls on size and duration.
- Applied where every burn passes (`covert_op_burn`'s target block, or beside it in `.1`'s
  `after`), not in `.2`, which has a 24-month cooldown and would skip it.
- `.2`'s text gets a line saying the public has turned on the attacker's friends at home,
  when it applied. If `.2` is on cooldown the defender sees the modifier on the interest
  groups only; acceptable.
- A watched operation causes none of this until it is exposed. Keeping quiet is a way to
  avoid stirring up the public at home (owner agreed).

### Relations block removed

Owner: the block goes away entirely; you can run anything against a friend and pay for it.

- Remove the relations gates from `possible`: `iw_no_good_relations_tt` (amicable) on
  election interference, financial subversion, infrastructure sabotage, communications
  disruption and ideological subversion; `iw_no_cordial_relations_tt` (cordial) on
  destabilization. Also destabilization's `requirement_to_maintain` clause that ends it
  once relations reach cordial (`covert_operations.txt` ~line 1558).
- **AI (owner, option c):** the six formerly blocked operations get `NOT = { covert_is_friend = { TARGET = scope:target_country } }`
  in their AI `will_propose`, so the AI doesn't start running them against friends (anti-goal
  above). The other hostile operations (industrial, military and space espionage, influence
  campaign, cultivate assets, secure material) keep their AI logic, which has no relations
  test today: the AI goes on spying on friends with them and pays the new backlash when
  caught. Where the action has a `will_break` that isn't `always = no`, it also ends such an
  operation once the target becomes a friend, after the usual `covert_ai_op_settled` wait;
  the two wartime operations keep `will_break = { always = no }` (their war-or-play gate
  ends them).
- **Launch preview:** when the target is a friend, the action's tooltip says so and what a
  catch would cost at home.
- **Kept:** the intelligence-sharing treaty gate (`iw_no_intel_sharing_tt`, on all 14
  operations). It is a treaty obligation, not the relations block. My call; listed for the
  owner to confirm.
- Remove the now-unused loc keys or leave them for the AI tooltips, whichever the builder
  ends up using; `loc_coverage_audit` and `script_loc_reference_audit` will say.

## C. Counterintelligence Support

A new operation, type `counterintel_support` (code 14), diplomatic action
`covert_counterintel_support_action`.

- **Who:** only a friend (`covert_is_friend`), checked in `possible` and in
  `requirement_to_maintain`, so the operation lapses if the friendship does. Allowed on an
  intelligence-sharing partner (the treaty gate is for hostile operations). The ally
  doesn't have to accept (`requires_approval = no`, like every operation).
- **What it costs:** an operation slot, upkeep (priority share as usual), and pact
  influence at the mild tier (25). Counts against the per-type cap.
- **What it does:** raises the target's economic, military and ideological covert defence
  (`country_covert_defense_*_add`). It goes through the usual phases (nothing while
  preparatory, from six months establishing, full at twelve) and the priority stepper, via
  `covert_op_add_scaled_modifier`. Starting unit, my call: +8 on each axis, so 8 to 26 per
  axis across phase × priority (1 to 3.2). Compare Heightened Vigilance, +25 for a while
  after a catch, and the UN's shared intelligence, +5 a step.
- **Several protectors:** a named modifier on one country doesn't stack with itself, so
  several protectors don't add up. Whatever the builder does, the target must end up with
  the strongest protector's value, not whichever pulse ran last.
- **Public, not hostile:** `is_hostile = no`; an ordinary visible pact. No detection roll
  (its row shows no detection figure), never caught, never burned. It still has to sit in
  exactly one tier trigger for the registry; mild is nominal.
- **Excluded from everything that treats an operation as hostile or as a foothold**
  (owner: the protector gets nothing). At least: `covert_nets_sync` steps 1 and 2 (no
  network inside the ally, no growth), the head start in `covert_op_create`, detection
  staging and the roll, Tradecraft gain, a network's tier-2 count of "operations against
  us", the UN dossier and docket, election confidence, the AI's priority manager if its
  levels assume a hostile target. The builder audits every reader of `iw_ops` for this.
- **Registry:** adding an operation type touches the sites listed under "Adding an
  operation type" in `mod_systems.md` (about fourteen); `test_covert_op_registry.py`,
  `test_covert_stand_down.py`, `test_covert_layout.py` pin them. It needs a place in
  `test_covert_tech_gates.py`: ungated is my call (`UNGATED`), since defence shouldn't
  wait on technology the attacker may not need.
- **AI:** proposes it for a friend whose intelligence capacity is below its own, preferring
  bloc members it leads, its subjects and its allies, with a free slot and the money (the
  existing `covert_ai_can_spare_influence` test). At most one at a time per AI country is
  my call. Breaks it when the friendship ends (the maintain check does that anyway) or the
  AI needs the slot.
- **Interaction:** the intelligence-sharing pact's shield reads the parties' defence
  modifiers, so Counterintelligence Support on one partner feeds that partner's side of
  the shield calculation. Check it can't loop or double-count.

## D. Research: hiding pacts and treaty articles from third parties

Read-only investigation of vanilla 1.14.5 script, GUI and the engine docs dump. Verified
from files unless marked.

- **No engine or script field hides a pact, treaty or article from third parties.**
  `diplomatic_action.md` documents none. `should_notify_third_parties = no` (vanilla uses it
  on `orchestrate_coup`, `support_separatism`, `fund_lobbies`; all 14 covert operations set
  it) suppresses the third-party notification feed only. `show_in_outliner` and
  `show_in_lens` affect the owner's own outliner and lens. Treaty articles have no secret
  flag; their `visible` trigger only decides who can put the article in a treaty.
- **Script sees everything.** `has_diplomatic_pact` works from any country scope and
  `any_treaty` is global, so any script (and the AI) can read any pact or treaty.
- **The AI reads game state directly.** Hiding GUI elements affects human players only.
  Vanilla AI never reads a mod pact type (all 13 `has_diplomatic_pact` uses in
  `ai_strategies/` name `rivalry` or `embargo`); third-party AI reacts to mod pacts only
  where mod script tells it to. How the engine's hardcoded AI treats `is_hostile` pacts is
  unknown.
- **Where a player sees other countries' pacts and treaties:** one file,
  `gui/country_panel.gui`, which the mod does not override. The pact list
  (`diplomatic_pact_container` → `diplomatic_pact_type_item` → `diplomatic_pact_item`) and
  the treaty list (`treaties_country_list`, `treaty_country_dropdown`,
  `compact_treaty_item`, `article_icon_all_items`) have no party filter. Other surfaces
  (outliner, map markers, the diplomatic overview) already show only the player's own.
  Filtering is possible with GUI functions that exist (`DiplomaticPact.IsFirstCountry` /
  `IsSecondCountry`, `Treaty.Binds`, `GetPlayer`, `Article.HasType`), at the cost of
  overriding that file or redefining its seven types from a mod file (which definition
  wins when a type is defined twice is untested). The type header row needs hiding too,
  or an empty "Covert operation" heading shows.
- **Leaks a GUI filter can't close:** the intelligence-sharing article's infamy is global;
  its modifiers show in the parties' breakdowns with the source named (inferred); a covert
  operation's modifiers on its target show in the target's tooltips.
- **Notifications** can't be filtered per action: one message type serves every
  diplomatic action. A player can mute a notification group in Message Settings; a mod
  can't do it for them.
- **Unverified, needs a game:** whether a covert operation's **target** gets a toast when
  it launches. Every covert action defines an `_action_notification_desc` addressed to the
  target ("[INITIATOR_COUNTRY] has launched an election interference campaign"), and
  vanilla's coup and separatism actions notify their targets. If it does, targets already
  learn of every launch by name, which undercuts detection as a whole (a pre-existing
  question, not caused by this design). Added to the play-test list.

**Options, cheapest first:**

1. Accept the leak (today).
2. Filter covert rows in `country_panel.gui` to the parties only. One file, compat cost of
   overriding it; doesn't close the modifier/infamy leaks; AI unaffected.
3. Model secret agreements without pacts (variables or containers on both parties, offered
   through events or the panel). No public footprint and no launch toast, but loses the
   diplomacy-panel negotiation, the AI accept scores and the outliner break button. The
   operations already keep their state in containers, so this is mostly a question of
   replacing the pact's cost, auto-break and AI hooks.

Recommendation: nothing now; if secrecy matters, verify the launch toast first, since it is
the bigger leak and option 3 is the only fix for it.

## Constraints

- House rules in `CLAUDE.md` and `docs/guides/scripting_best_practices.md`: days not months
  for `*_modifier_time`; `any_*` takes no `limit`; register every new modifier type; loc
  for every new key (no engine warning for a missing one); tab indentation; one BOM.
- Event ids: next free in the `covert_warfare` namespace; the hidden exposure event the
  panel orders too. Every visible event needs `event_image` (`event_image_audit`).
- `change_variable` / `set_variable` render nothing in tooltips: the Let it run option
  must say what it does in `custom_tooltip` (`silent_variable_audit`).
- `je_immediate_reset_audit`: new state on the journal entry's country must survive a
  civil war's winner (variables, not modifiers or lists, for anything that has to persist;
  the records are containers, which the winner doesn't inherit; a lost watch list on
  revolution is acceptable, my call, but say so in the code).
- Player guide: `docs/player_guide/11-influence.md` (Covert Warfare sections: "The covert
  operations", "Detection and exposure", "What the target learns", "Covert defense",
  "How the AI runs covert operations") gets the new operation's row, watching and the
  Known Foreign Operations section, the backlash, and the removed relations block. Rebuild
  the PDF. Style: `docs/player_guide/STYLE.md`.
- System docs: `mod_systems.md` § Covert Warfare; `journal_entry_systems.md` § Covert
  Warfare → Panels (a CRLF file: edit without flipping line endings).
- Record the § D findings where the next agent will look: a short note in
  `docs/guides/scripting_best_practices.md` (no visibility field on pacts or articles) and
  `docs/guides/gui_modding_guide.md` (where other countries' pacts render, CRLF).
- In-game checks don't gate the merge (owner rule): a new play-test list,
  `docs/testing/covert-counterintel-playtest.md`, with the Expose button's container link,
  the defender decision event, the appeasement factor's tooltip line, and the launch-toast
  question.

## Left to the builder

- Variable, modifier, loc and event names; exact layout of the new panel section.
- Whether the backlash lives in new scripted effects or inline in `.1`'s options (prefer
  one effect shared by both options, parameterized by the home share).
- The tuning figures marked "starting" above.
- Splitting into commits or PRs (one branch, one PR with a commit per part is fine).

## My calls, for the owner to check

1. Friend = cordial + a tie, or amicable without one.
2. A defender with no covert service gets today's flow, no decision popup.
3. Watch growth: 4 a month at priority 1, × 1.35 / 1.6 at priorities 2 and 3.
4. AI watch odds and monthly expose odds as listed in § A.
5. Legitimacy −3 / −5 / −8 by tier for 2.5 years, decaying; relations ×1.5 abroad when the
   target was a friend.
6. Defender side: −5% / −10% / −15% political strength on the pro-attacker lobby's groups,
   ×1.5 for a friend, 2.5 years, decaying.
7. (Owner chose option c; see § B.) AI `will_break` on the formerly blocked operations waits for `covert_ai_op_settled` like other breaks.
8. The intelligence-sharing treaty gate stays on all hostile operations.
9. Counterintelligence Support: +8 per axis unit, mild-tier influence (25), ungated by
   technology, AI runs at most one.
10. Watch records are lost if the defender's government falls to a revolution.
11. One exposure in flight per attacker; a player's Expose can wait up to three days.
