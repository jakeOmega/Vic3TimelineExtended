# Nuclear umbrella for subjects, Recessed readiness, Automatic Retaliation — design

## Context

The owner's list from the first nuclear-crisis play-test (2026-09-25,
`2026-09-25-nuclear-crisis-communication-design.md`) left two items as new mechanics for their own pass:

- **Item 4.** Overlords should give their subjects a nuclear guarantee by default, revocable at a liberty-desire cost.
- **Item 7.** Should there be a readiness below Routine, or more launch authorities? Claude recommended a
  **Recessed** readiness and an **Automatic Retaliation** ("Dead Hand") launch authority; the owner asked for both.

Baseline: `main` at `b84eae02` (#452 and #454 merged). `docs/systems/nuclear_crisis_design.md` §0 is what the code does
today; this document changes §0.2 (posture), §0.3 (crisis figures), §0.4 (incidents) and §0.5 (guarantees).

## Decisions (owner, 2026-09-25)

| Question | Decision |
|---|---|
| How withdrawing a subject's umbrella costs liberty desire | A **lasting subject-relation pact** like vanilla Raise Subject Payments (+0.10 liberty desire a week while it stands) **plus a one-off** +10 liberty desire and −20 relations when it is made. Cancelling the pact restores the umbrella |
| Does a nuclear strike on a covered country license the guarantor's retaliation? | **Yes, under every doctrine** (No First Use included: answering a nuclear strike on a protected country is not first use). And the guarantor need not already be at war with the attacker: **answering the strike pulls the guarantor into that war** |
| What Recessed prevents | **No launch of any kind until readiness is back at Routine** — but the licence to retaliate for a strike taken while recessed **persists until the forces are ready**, if the country survives that long |
| What Automatic Retaliation fires | **Full retaliation**: three warheads (fewer if fewer are left), with no option to absorb the strike or answer in measure |
| Coverage depth, abandonment, AI (Claude's defaults, not contested) | Direct subjects only; the overlord must be believed armed. Abandoning a subject in `.20` also costs +10 liberty desire and does not withdraw the umbrella. The AI never withdraws an umbrella |

**Claude's reading of "pull the guarantor in" (flag if wrong).** The guarantor is not put into the war automatically:
the guarantee event (`nuclear_crisis.20`) still asks it, and its Honour and Retaliate options now *join the war on the
beneficiary's side* when it is not already in it. Walking away keeps its existing costs. This keeps §6's rule that a
guarantee is not an automatic declaration of war, while making "they used the bomb on someone we protect" the moment the
guarantor can come in.

## Constraints the design works inside

- **Tooltip passes.** Event options, diplomatic-action `accept_effect`s and scripted-GUI effects are re-walked for their
  tooltips every frame without running. Anything shown there reads only scopes that exist in the preview (the event's own
  saved scopes; ROOT and `scope:target_country` in a diplomatic action). Launches stay behind the fenced dispatch
  helpers (`nd_dispatch_*`), which do nothing in a preview.
- **`change_variable` renders nothing**: every visible variable write in an option gets a `custom_tooltip` with its
  number (`silent_variable_audit --strict`).
- **`nd_readiness_mod_on` uses 0 for "no modifier"**, and is set to `var:nd_readiness`. Recessed is readiness 0, so it
  carries **no readiness modifier** (as Routine carries none); otherwise the tracker could not tell "Recessed's modifier
  is on" from "none is on".
- **Stored values stay valid.** Recessed is `nd_readiness = 0` and Automatic Retaliation is `nd_authority = 4`, so no
  existing save changes meaning and every existing `>= 2` / `= 3` test keeps its sense. Every test that reads `= 1` as
  "the lowest readiness" or `>= 2` as "anything but central" is audited below.
- **No first-strike bookkeeping for a retaliation.** Retaliation keeps `nuclear_response_strike` (the `.1` path);
  `nd_dispatch_strategic_strike` would book it as a first strike (+25 infamy, the first-strike UN dossier).
- **`join_war`** (war scope: `join_war = { target = <country> side = <country> }`) is used by vanilla
  (`44_enforce_military_access.txt`) and by `events/world_war_events.txt`. Whether it refuses a country under a truce
  with the attacker is not known: **verify in game**.
- **Loc style.** `#b`/`#v`/`#R`/`#G`; explanatory, causal wording; new key families get `organize_loc.py` rules where
  they need them. `$PARAM$`-built keys land in `te_unused_l_english.yml` (#451): expected, not a regression.

## 1. Item 4 — the nuclear umbrella

### 1.1 Who is covered

A country is **under its overlord's umbrella** when it is a **direct** subject (`is_direct_subject_of`) of a country
that is believed armed (`nd_believed_armed`: holds `nuclear_power`), and no withdrawal pact (§1.3) stands between them.
Coverage by umbrella is **the same thing** as coverage by a `nuclear_guarantee` treaty article: every effect of §0.5
applies — the war-support shadow is lifted, an attacker's AI counts the overlord's arsenal, the crisis pressure term,
dispute 3, the guarantee event when the subject is warned or struck, the abandonment ripple.

A subject of a subject is covered by its own direct overlord only. An armed subject is covered like any other; its own
arsenal already counts for itself.

### 1.2 One definition of "covered", used everywhere

Today eight sites read `nuclear_guarantee` articles directly. They are all rerouted, so the treaty and the umbrella
cannot drift apart. The triggers, in `nuclear_deterrence_triggers.txt`:

| Helper | Meaning |
|---|---|
| `nd_under_umbrella_of = { OVERLORD = X }` (trigger) | this country is X's direct subject, X is believed armed, no withdrawal pact |
| `nd_is_guaranteed_by = { GUARANTOR = X }` (existing, extended) | a treaty article from X, **or** under X's umbrella |
| `nd_is_guaranteed` (existing, extended) | covered by anyone |
| `nd_has_armed_guarantor_against = { AGAINST = X }` (existing, extended) | covered by someone believed armed who is not X |
| `nd_guarantees_someone_against = { TARGET = X }` (new trigger, guarantor scope) | dispute 3's test: someone we cover is in a play or war against X (replaces `nd_dispute_guarantee_against`'s body) |

The triggers are shared. The three effect loops (notify the target's guarantors, the victim's guarantors, the other
beneficiaries after an abandonment) cannot share one helper — a scripted effect cannot take an effect block as a
parameter — so each keeps its treaty loop and gains a sibling branch beside it: `overlord ?= { limit-equivalent … }` for
"my guarantors", `every_direct_subject = { limit = { nd_under_umbrella_of = { OVERLORD = scope:… } } … }` for "my
beneficiaries". Each sibling carries a comment naming the other two, and the static test in §5 fails if a
`has_type = nuclear_guarantee` read appears outside the known sites.

Sites (all rerouted): `nd_has_armed_guarantor_against`, `nd_is_guaranteed`, `nd_is_guaranteed_by`,
`nd_dispute_guarantee_against` (triggers); `nd_crisis_classify_dispute` (dispute 3's beneficiary),
`nd_crisis_notify_guarantors`, `nd_record_nuclear_use` (guarantors of the victim), `nd_guarantee_act_abandon`
(other beneficiaries) (effects); `zz_te_war_support_injections.txt` reads `nd_has_armed_guarantor_against`, so it
follows for free. `events/te_debug_deterrence_events.txt:327` creates a treaty article for the harness and stays
treaty-specific.

**No double coverage.** The `nuclear_guarantee` article's `possible` refuses a pair where the beneficiary is the
guarantor's direct subject (new `custom_tooltip`: "they are already under our nuclear umbrella"). A treaty signed
before a subjugation can survive into it; the loop helpers skip the umbrella branch when a treaty article between the
same pair exists (the treaty branch already covers it), so `.20` fires once.

### 1.3 Withdrawing and restoring the umbrella

A new diplomatic action in `common/diplomatic_actions/nuclear_umbrella_actions.txt`:

- `nd_withdraw_umbrella_action` — "Withdraw Nuclear Umbrella". `groups = { overlord }` (precedent without a DLC gate:
  `annex_subject_peaceful` in `extra_diplo_actions.txt`), `requires_approval = no`.
- `potential`: nuclear weapons rule on; the target is our direct subject; we are believed armed.
- `possible`: the target is under our umbrella (i.e. not already withdrawn).
- `accept_effect` (all visible in the confirmation box): the target gains **+10 liberty desire**
  (`add_liberty_desire = 10`, the size of vanilla law imposition); **−20 relations** with us; a custom tooltip naming
  what the subject loses (no war-support shadow relief, no guarantee event, no crisis protection).
- `pact`: `second_modifier = { country_liberty_desire_add = 0.10 }` — the subject's liberty desire rises 0.1 a week
  (≈ 5 a year) while the pact stands, the same rate as vanilla Raise Subject Payments. `requirement_to_maintain`: still
  our direct subject (the pact dies with the relationship). `break_string` = "Restore Nuclear Umbrella"; breaking it is
  free and restores coverage at once. No `forced_duration`: flip-flopping pays +10 each time.
- `ai`: `will_propose = { always = no }`; `will_break = { always = yes }` (an AI that inherits a withdrawal restores it).
- The pact's type is what `nd_under_umbrella_of` tests (`any_scope_diplomatic_pact = { is_diplomatic_action_type =
  nd_withdraw_umbrella_action … }`, the covert-comms precedent in `nuclear_deterrence_values.txt`).

### 1.4 Abandoning a subject

`nd_guarantee_act_abandon` (the `.20` "walk away" option), when the beneficiary is under our umbrella, also gives it
**+10 liberty desire**, shown in the option. It does not withdraw the umbrella; the existing −15 credibility,
`nd_guarantee_abandoned`, −30 / −10 relations stay.

### 1.5 Extended deterrence: a strike on someone we cover

- **Licence.** `nd_was_struck_by = { ENEMY = X }` also holds when **a country we cover** (treaty or umbrella) was struck
  by X (its `nuked_by_country` is X) and we are at war with X. Everything that reads it follows: the doctrine permission
  (so every doctrine, No First Use included, may answer), the pledge permission, the No-First-Use-breach exemption in
  `nd_record_nuclear_use`, and the AI's `nd_ai_nuclear_use_justified`. Because `nuked_by_country` persists, the licence
  lasts as long as the war does.
- **Pulled in.** In `nuclear_crisis.20` after a strike (`nd_guarantee_context = 2`):
  - **Honour** — if we are not in the beneficiary's war with the attacker, **join it on the beneficiary's side**
    (`join_war`, in the war where the attacker and the beneficiary are enemies); credibility +5; the existing relations
    and `.21` notice. The old "open a public ultimatum" branch is kept only for a strike with no war to join (it cannot
    happen today — every strike needs a war — but the branch costs nothing to keep and guards a future peacetime path).
  - **Retaliate** — join as above if needed, then answer through the retaliation path (`nuclear_response_strike`
    semantics, not a first strike); credibility +10. Available whenever we are armed, our forces are assembled (§2.3)
    and no pledge with the attacker stands; no longer greyed for want of our own doctrine's permission, and no longer
    needs us to be at war beforehand.
  - **Abandon** — unchanged, plus §1.4.
- The `.20` option texts say what joining means ("We enter the war against X on Y's side").
- A strike on a covered subject whose overlord is already its war leader needs no join; the options skip it.

### 1.6 What the player sees

- The posture panel's Forces section gains one line when we have covered subjects: "Nuclear umbrella: covers N
  subjects" (`nd_display_umbrella_count`), with a tooltip saying what coverage does and how to withdraw it.
- The withdraw action's confirmation box shows the liberty desire, relations and what the subject loses.

## 2. Item 7a — Recessed readiness

### 2.1 The level

`nd_readiness = 0`, "Recessed": warheads stored apart from their delivery systems (India's and Pakistan's posture after
1998). It sits below Routine on the same axis: one step every two weeks, so Recessed → Routine takes two weeks and
Recessed → High Alert six. Lowering is never blocked; a conceded or agreed stand-down holds readiness *at or below*
Routine, so it permits Recessed. New arsenals still start at Routine.

### 2.2 What it changes

| | Recessed | (Routine, for comparison) |
|---|---|---|
| Readiness upkeep | none | none |
| Custody upkeep | 0.1 units per warhead | 0.2 |
| Incident base odds | 0.5 ‰ a month | 1 ‰ |
| Strain | falls 6 a month (as Routine) | falls 6 |
| Crisis danger, own readiness part | −8 (the existing `(readiness − 1) × 8` formula, now allowed below zero for this part only) | 0 |
| Pressure on a target, issuer recessed | **−10**, a new named part `nd_yp_recessed` ("the threatening side's weapons are not mated to their delivery systems") | 0 |
| At home | Restraint groups **+1**; Professional officers **−1** (always, not only against a plausible attacker); Militarists −1 (as Routine) | officers −1 against a plausible attacker |
| Launches | **none** (§2.3) | permitted |

No readiness modifier (Constraints). The incident roll's inner `chance` already takes fractional per-mille values
(Routine at high reliability runs 0.5 ‰ today, §0.4's table), so 0.5 ‰ needs no third stage.

### 2.3 The launch gate

`nd_forces_assembled` (new trigger): `nd_readiness` is missing or ≥ 1. It is required, with its own failure line
("Our warheads are stored apart from their delivery systems: Routine readiness is two weeks away"), by:

- the strategic and tactical strike actions in `nuke.txt` (`possible`) and their AI `will_propose` (through
  `nd_ai_nuclear_use_justified`);
- `nd_retaliation_permitted` (the retaliation options in `nuclear_weapon_events.1` and `.11`);
- `.20` Retaliate, and every crisis option that can end in a strike (`.4.g`, `.7.a`);
- both dispatch fences (`nd_dispatch_strategic_strike`, `nd_dispatch_tactical_strike`), so no incident branch can launch
  from a recessed force;
- the Monopoly Window's eligibility.

Incident eligibility: the Unconfirmed Warning and The Exercise They Mistook already need readiness ≥ 2; Silence from
the Capital additionally needs `nd_forces_assembled` (a cut-off commander has nothing to launch).

### 2.4 Struck while recessed: the licence waits for the forces

When a strategic strike lands on a recessed country (`nuclear_weapon_events.1`):

- The retaliation options show as unavailable with the reason above. A new option, **"Assemble our weapons and answer
  when ready"**, sets the readiness target to at least Routine and records the pending answer:
  `nd_pending_retaliation` = the attacker (a variable on the struck country). The default option ("absorb") records
  nothing and leaves readiness alone.
- Under Automatic Retaliation (§3), assembling is the standing order: the event's only option assembles and records the
  pending answer; nothing else is offered.
- When readiness reaches Routine (the weekly readiness step), if `nd_pending_retaliation` is set, **still at war with
  that country, still armed, and it still exists**, a new event `nuclear_weapon_events.24` "Our Forces Are Ready" offers
  the answer: one warhead, full retaliation, or stand down (clears the record). Under Automatic Retaliation it fires the
  full answer in its only option. The answer uses the same strike and record effects as `.1` options b / c, with the
  attacker as the victim. If any condition fails, the record is dropped silently.
- The strike actions in the diplomacy view stay available to it throughout the war once assembled (the licence persists,
  §1.5).

### 2.5 AI

- The review picks Recessed when: at peace, not in a crisis, no plausible attacker (`nd_has_plausible_attacker = no`),
  not militarist, and at least one of — a cautious ruler, No First Use doctrine, in default.
- **Stepping out.** An AI at Recessed that finds itself at war or in a crisis sets its target to at least Routine in its
  monthly update (not waiting for the six-monthly review), and the crisis-open review (`nuclear_crisis.99`) does the
  same. The pending-answer choice in `.1` weighs "assemble" by `nd_ai_nuclear_use_justified`-style retaliation appetite.

### 2.6 Sites that read "lowest readiness" or clamp at Routine (audit)

| Site | Today | With Recessed |
|---|---|---|
| `nd_readiness_step_down` (an accident's forced stand-down) | steps down while target ≥ 2 | unchanged: a forced stand-down stops at Routine |
| Crisis concession "readiness to routine" (`nuclear_crisis_effects.txt` ~1339) and `nd_standdown_one_side` (~1615) | **set** the target to 1 | set it to 1 **only if it is above 1** — otherwise a Recessed country would be *raised* by a stand-down. The lock is set either way |
| Dispute 5 resolved: "the alert was stood down" (~733) | target `= 1` | target `<= 1` |
| Hold at high alert (~1666): "four weeks" vs "two weeks" text | readiness `= 1` → 4 weeks | readiness 0 → a new "six weeks" line |
| Counter-threat raises to Heightened (~1513) | target `< 2` → 2 | unchanged (raises from 0 too) |
| `te_event_agency_misc_triggers.txt:84`, `nuclear_incident_events.txt:443, 553` (raise by one / to 3) | target `< 3` | unchanged |
| Domestic readiness terms (`nuclear_deterrence_values.txt` ~1064, ~1087) | `= 1` is the low end | add the Recessed row of §2.2 |
| `nd_readiness_or_routine` (danger parts) | 1 when missing | unchanged; a stored 0 yields the −8 of §2.2 |
| `nd_strain_step`, `nd_incident_permille`, `nd_upkeep_units*`, `nd_upkeep_weekly_at_readiness_*` | levels 1–3 | add level 0 |
| `nd_set_readiness_target_*`, `nd_can_set_readiness`, the AI review's readiness block | 1–3 | add 0 |
| Custom loc `nd_readiness_name`, `nd_readiness_moving` | 1–3 | add 0 |

## 3. Item 7b — Automatic Retaliation

### 3.1 The setting

`nd_authority = 4`, "Automatic Retaliation" (the Soviet Perimeter system, 1985): if our territory is struck, the
answer is launched without a further decision. It needs `radar`, `ICBMs` and `mainframe_computers` (era 7), and the
12-month authority tenure like the others. The panel gains a fourth authority row (op 34).

### 3.2 What it buys

- **Certain retaliation.** In a crisis where we are the target, "can they answer in kind" (`nd_yp_answer_value`) scores us
  as survivable (−25) whatever our survivability. A vulnerable arsenal deters like a survivable one — the reason such
  systems were built.
- **No hair trigger on warnings.** The Unconfirmed Warning goes to the government, exactly as under Central
  Authorization (the system waits for detonations, so leaders can wait for proof). Silence from the Capital does not
  apply (there are no delegated commanders).

### 3.3 What it costs

- **Full retaliation, no choice.** When a strategic first strike lands on us (`nuclear_weapon_events.1`) and our forces
  are assembled, `.1` has one option, "The System Answered": three warheads at the attacker (fewer if fewer are left),
  through `.1`'s existing full-retaliation effects, recorded once with `nd_record_nuclear_use`. Its tooltip renders the
  strikes. No absorbing the blow, no measured answer.
- **Accidents read as attacks.** In The Cost of Permanent Alert (`nuclear_incident.30`), a bomber break-up with weapons
  aboard (kind 1) or a silo explosion (kind 2), while at war or in a crisis at stage 3, can set the system off: a hold
  roll (`nd_hold_chance`) decides; an unheld launch goes through `nd_launch_or_intercept` against the most likely
  attacker (the crisis opponent if armed, else an armed enemy) — a strike in a war, an intercepted order outside one — and
  the event's text says so. One branch in `.30`, not a new chain.
- **Upkeep** +3 units (as one hardening level).
- **At home.** Restraint groups −1, as for Launch on Warning.

### 3.4 Bounding it (design doc §11)

- It fires **only** from `.1` — a first strike on us. `.11` (being answered after our own strike) never fires it
  automatically, so two Dead Hands cannot empty each other's arsenals: A strikes B, B's system answers, A chooses.
- A per-attacker cooldown: after an automatic answer to X, `nd_auto_answered_months` (6) blocks a second automatic
  answer to X; `.1` then offers the normal choices. Stock is revalidated by the existing effects.
- Tactical strikes (`nuclear_weapon_events.5`) do not set it off: the system listens for city-scale detonations.

### 3.5 Sites that read "delegated or launch on warning" (`nd_authority >= 2`)

`nd_authority_delegated_or_warning` becomes explicit (`= 2` or `= 3`) and a new `nd_authority_automatic` (`= 4`) is
added. Readers: `nd_incident_eligible_commander` and Silence from the Capital's own trigger
(`nuclear_incident_events.txt:910`) (2–3 only), the Unconfirmed Warning's routing in `nd_start_unconfirmed_warning`
(2–3 only; 4 routes as Central), `nd_hold_chance` (no change), `nd_ai_want_safeguards` (4 counts, like 2–3), the
domestic authority term (Restraint −1 at 3 and now 4), the authority consequence tooltip
(`nd_tt_authority_consequence` gets a variant for 4: "a strike on us will be answered in full without a decision").

### 3.6 AI

The review adopts Automatic Retaliation (25 % per review) when it can, has a plausible armed attacker, survivability
< 50, is not cautious, and would not take Launch on Warning (a non-militarist regime). A cautious ruler returns to
Central as today.

## 4. Panel, loc, op codes

- `nd_posture_sgui`: op **20** = readiness target 0, op **34** = authority 4. The op tables in the sgui header, the
  widget header and `docs/systems/journal_entry_systems.md` (CRLF — edit preserving line endings) are updated together.
- Widget: a Recessed row above Routine and a fourth authority row, each with a tooltip in the style of their siblings
  (what it is, what it buys, what it costs, upkeep at that level; for Automatic Retaliation the `#R` consequence line).
  The readiness legend: "An agreed or conceded stand-down holds it at Routine or below".
- Custom loc: `nd_readiness_name` / `nd_authority_name` gain the new values; `nd_readiness_moving` handles 0.
- New loc for: the withdraw action (name, desc, confirmation lines, pact break string), the umbrella line and tooltip,
  `nd_yp_recessed_line`, the assembly option and `.24`, `.1`'s "The System Answered", `.20`'s joining lines, the `.30`
  system branch text, the recessed launch-gate failure line, the Automatic Retaliation tooltips.

## 5. Testing

- `test_nuclear_deterrence.py`: extend the op-table test (20, 34), the fired-event and loc-key tests (`.24`, new keys),
  and the modifier-family test if it enumerates readiness members. Add a static test that every `nuclear_guarantee`
  reader outside the helpers is gone (grep-style: `has_type = nuclear_guarantee` appears only in the helper file, the
  article file and the debug harness).
- `scripts/analysis/nuclear_incident_rates.py`: add Recessed rows (and an Automatic Retaliation row whose "launch orders
  not held" count is the accident branch only), and update §0.4's table.
- The `--strict` audits and the full unittest suite in the worktree (with the dummy `VIC3_*` env vars), `ruff`, the tab
  check, the localisation checks. A second mod-state server on another port from the worktree for a reload check
  (`docs/guides/python_tools.md` § Starting the Server), reading the reload `warnings`.
- Console harness (`events/te_debug_deterrence_events.txt`): set readiness 0 / authority 4 on the player; give the player
  an armed overlord relation test via the existing guarantee harness where feasible.
- In-game checklist: new items appended to `nuclear_crisis_design.md` §0.9 (umbrella coverage and `.20` for a subject;
  the withdraw action's confirmation box and the pact's liberty-desire line; a strike on a covered country under
  Existential Deterrence offering Retaliate; `join_war` pulling a treaty guarantor in (and whether a truce blocks it);
  Recessed greying every launch and the assemble-then-answer path through `.24`; Automatic Retaliation's single `.1`
  option and its cooldown; the `.30` system branch).

## 6. Docs

`docs/systems/nuclear_crisis_design.md` §0.2 (readiness 0–3, authority 1–4, the tables), §0.3 (the new pressure part),
§0.4 (incident odds and routing, the `.30` branch, the rates table), §0.5 (the umbrella, the licence, joining), §0.9;
`docs/systems/journal_entry_systems.md` op table; `docs/systems/mod_systems.md` if it summarises the posture axes.

## Out of scope

- Umbrellas for power-bloc members, or from a top overlord to subjects of subjects.
- An AI that withdraws umbrellas.
- Automatic entry into a war without the guarantor's choice (see "Claude's reading" above).
- A peacetime strike path, a genuine-warning variant, or any change to the Launch on Warning or Conditional Delegation
  chains beyond the explicit `>= 2` audit.
