# Nuclear crisis: say what it does, price bluffs, and IG classes by Rules of War — design

## Context

The first play-test of the nuclear crisis system (shipped 2026-09-25, `docs/systems/nuclear_crisis_design.md` §0) was a
public ultimatum to Canada in a minor war, under Existential Deterrence. Canada proposed a stand-down, the player refused,
and some weeks later Canada conceded. Every step worked, and the player could not tell what any of it did. The owner's
list (2026-09-25):

1. The ultimatum's tooltip says "opens a public nuclear crisis — deadline eight weeks". It does not show the +5 infamy,
   the −20 relations, the stage, what the target gives up by conceding, or that the crisis is followed in the journal
   entry.
2. Event option tooltips don't make the mechanics clear.
3. The outcome event ("The Demand Is Met") shows neither the credibility gain nor the target's lost war support.
4. Overlords should give their subjects a nuclear guarantee by default, revocable at a liberty-desire cost.
5. Under Existential Deterrence, in a minor war, why could the ultimatum be issued at all?
6. "At Home" names a mood (Opposed, Uneasy…) but not the approval number the IG screen shows.
7. Should there be a readiness below Routine, or more launch authorities?
8. Any other improvements.

**This document covers 1, 2, 3, 5 and 6, plus the item-8 ideas that belong to them.** Items 4 (overlord umbrella) and
7 (new posture tiers) are new mechanics and get their own design passes afterwards.

**Answer to 5, as found.** `nd_can_open_crisis_against` asks for an arsenal, both sides free, the cooldown, a dispute
(being at war is one) and no pledge. Doctrine gates only *carrying out* the threat (`nd_doctrine_permits_strike`, read
by the deadline event's strike option and the strike actions). So the ultimatum was a pure bluff — and it worked,
because `nd_yield_pressure_value` never reads the issuer's doctrine. Neither the AI nor the player could tell a bluff
from a threat.

## Decisions (owner, 2026-09-25)

| Question | Decision |
|---|---|
| Bluffs (a threat the doctrine forbids carrying out) | **Allowed, and priced in**: a warning in the tooltip, a large pressure penalty (doctrine is public), extra credibility cost when a public bluff is called |
| At Home classes | Armed Forces = professional officers; Industrialists = business; every other IG classed by its **Rules of War** law stance |
| Strength | approving a law = a mild opinion (capped ±1); strongly approving = full (±2) |
| Armed Forces and Industrialists | keep their own concerns, and their Rules of War stance adds militarist or restraint *doctrine* terms (a "lean") |
| At Home layout | **one row per interest group**, with its class and approval number; the tooltip itemises it |
| Crisis panel moves | show only the moves our side can make; greyed with a reason when they apply but are blocked |
| Outcome consequences | applied in the outcome event's option, so its tooltip renders them (the owner's standing rule: grant event effects in the option, not in a broadcast before it) |
| Split | two PRs: **PR 1** = §1–§3 (crisis), **PR 2** = §4 (At Home) |

## Constraints the design works inside

- **Tooltip passes.** The engine re-walks a diplomatic action's `accept_effect` and every option's effects each frame
  the box is open, without running them, and evaluates limits and saved scopes inside `hidden_effect` too
  (`nuclear_crisis_effects.txt` header; `scripting_best_practices.md` § Per-Entity State rule 6). Saved scopes made
  inside the effect do not exist in the preview. Anything shown in a preview must read only scopes that exist there:
  ROOT and `scope:target_country` in the diplomatic actions; the event's own saved scopes in events.
- **`change_variable` renders nothing.** Every visible variable write in an option needs a `custom_tooltip` naming it
  with its number (#446's `nd_tt_credibility_*`, `nd_tt_strain_*` pattern). `silent_variable_audit --strict` enforces
  this in CI for variables the UI reads.
- **No `save_scope_value_as`.** It is not in this engine's `effects.log`, so a number cannot ride along a
  `trigger_event` as a scope value. Events that must know "which outcome" read a record on the country, guarded by a
  token (the `nd_crisis_event_token` pattern).
- **IG-scope variables have no vanilla precedent.** The data types exist for the display (`Country.AccessActiveInterestGroups`,
  `InterestGroup.MakeScope`), and `set_variable` is documented for any scope. §4 lists the fallback.
- **Loc style.** `#b`/`#v`/`#R`/`#G` formatting, never `[b]`; explanatory, causal wording
  ("Canada's war support falls by 35", not "concession: war support"); new key families need `organize_loc.py` rules if
  their base has 4+ tokens.

---

## §1 Bluffs are priced in (item 5)

### 1.1 Follow-through

Two new scripted triggers, issuer scope, `$TARGET$` = the country threatened. They work in the diplomatic action preview
(`TARGET = scope:target_country`) and in a live crisis (`TARGET = scope:nd_target`).

| Level | `nd_threat_backed = { TARGET }` / `nd_threat_uncertain = { TARGET }` |
|---|---|
| **Backed** | At war with the target: our doctrine permits a strike now (`nd_doctrine_permits_strike`), **or** our doctrine is Compellence or higher (a defied public ultimatum, or a crisis past the warning stage, licenses it). Not at war: Compellence or higher. **And** the war-law gate permits a strike (§1.4). |
| **Uncertain** | Not at war, and either Flexible first use, or Existential deterrence when the dispute protects a country we guarantee (dispute 3) or the target's war goals in the play fall on our incorporated states (`nd_core_threatened_by`). |
| **Bluff** | Anything else. |

The level is evaluated live, so a doctrine change or a war turning against us moves it the same week.

### 1.2 Pressure

`nd_yield_pressure_value` becomes a sum of named component values, each its own script value in target scope reading
`scope:nd_issuer` (all exist today as inline terms; the new one is follow-through):

| Component | Value |
|---|---|
| `nd_yp_base` | 30 |
| `nd_yp_answer_in_kind` | +20 not believed armed / −25 survivability ≥ 50 / −10 otherwise |
| `nd_yp_protector` | −20 armed guarantor not walked away; −15 more once it has said it stands with us |
| `nd_yp_credibility` | (issuer credibility − 50) / 2 |
| `nd_yp_alert` | +10 issuer at high alert |
| `nd_yp_danger` | danger / 5 |
| `nd_yp_exercise` | +10 during a visible exercise |
| `nd_yp_temperament` | −15 aggressive ruler / +10 cautious ruler |
| `nd_yp_war` | +15 losing the war to the issuer; −15 the issuer threatens our existence |
| **`nd_yp_follow_through`** (new) | **+10 backed / 0 uncertain / −25 bluff / −35 bluff under No first use** |

The total is still clamped 0–100 and rounded. Each component is read by three displays — the panel's pressure tooltip
(§3), the event tooltips (§2) and, where the scopes allow, the diplomatic action (§2.1) — so the display is the formula.
`nd_crisis_danger_value` gets the same treatment (`nd_cd_*` components, including its ×0.7 for an unarmed, unguarded
target, shown as its own line).

### 1.3 A called bluff costs more

When a public crisis closes with the issuer backing down (outcomes 2, 5) or lapsing (8) while `nd_threat_backed` and
`nd_threat_uncertain` are both false, the issuer loses a further **5** credibility, with its own tooltip line.

### 1.4 The war-law gate (bug found while designing)

`nuke.txt`'s strike actions require the Rules of War law to allow a strike (strategic: neither Humanitarian
Regulations nor Limited War; tactical: not Limited War) unless we were struck or face an annexation-type war goal. The
crisis strike options — the deadline's "carry out the threat" (`nuclear_crisis.4.g`), "they chose war" (`.7.a`), and the
guarantor's retaliation (`.20.b`) — check doctrine and pledges but **not** the law, so a country under Limited War can
strike through a crisis.

Fix: move the strategic gate into `nd_war_law_permits_strategic_strike = { ENEMY }` (and the tactical one into
`nd_war_law_permits_tactical_strike`) in `nuclear_deterrence_triggers.txt`, called from both `nuke.txt` actions and all
three crisis options, with a `custom_tooltip`. `nd_threat_backed` requires the strategic gate.

### 1.5 The AI

- `nd_ai_would_issue_ultimatum` adds `nd_threat_backed = { TARGET = $TARGET$ }`: the AI never makes a public bluff.
- `nd_ai_would_warn`'s coercion branch (a hawkish doctrine or regime against a target that cannot answer) adds
  `OR = { nd_threat_backed  ruler_is_aggressive }`: private bluffs only under an aggressive ruler.
- The target's AI needs no change: it reads `nd_yield_pressure`, which now carries the bluff.

---

## §2 The tooltips say what happens (items 1, 2, 3)

### 2.1 The Private Warning / Public Ultimatum

`accept_effect` shows, in order:

1. **Engine-rendered effects.** `change_infamy = 5` (ultimatum) and `scope:target_country = { change_relations … }`
   (−20 / −5) move out of `nd_crisis_open`'s `hidden_effect` into a visible block before it. `possible` already demands
   `nd_crisis_parties_free`, so the crisis always opens when these run. The other callers of `nd_crisis_open`
   (`nuclear_incident.5` option c, `nuclear_weapon_events.18` option a) gain the same lines.
2. **The dispute and its concession**, one `custom_tooltip` per dispute, chosen by the same triggers, in the same
   priority, as `nd_crisis_classify_dispute`:
   "Over: our war with [target]. If they concede, their war support in that war falls by #R 35#!." /
   "Over: the diplomatic play. If they concede, they back down and our side wins it." / the guarantee, proliferation
   and alert variants.
3. **Follow-through** (§1.1): "#G Backed:#! our doctrine lets us carry this out if they defy it." /
   "#Y Uncertain:#! …" / "#R A bluff:#! Existential Deterrence permits a first strike only when they threaten our survival,
   or our territory while we are losing. They know our doctrine: their pressure to concede falls by 25."
4. **Pressure factors** that the preview can evaluate from ROOT and `scope:target_country` — answer in kind, protector,
   follow-through, their temperament, the war — one line each with its number. **Total:** only if a preview-safe
   script value can compute it (a planning spike: the live formula reads `scope:nd_issuer`, which the preview lacks); if
   not, the list stands alone and says "starting pressure is shown in the journal entry".
5. **Stakes:** "If they concede, our #v credibility#! rises by #G 15#! (public) / #G 10#! (private). If we back down, it
   falls by #R 15#! / #R 5#!; if the deadline lapses unanswered, by #R 10#!." Plus the called-bluff line when it applies.
6. **What happens next:** "The crisis opens at #v Confrontation#! (public) / #v Warning#! (private). They answer now,
   and are pressed again every six weeks; our deadline is eight / ten weeks. Follow it in the #v Nuclear Weapons#!
   journal entry."

### 2.2 The crisis acts

Every `nd_crisis_act_*` keeps its prose line and adds number lines (`custom_tooltip` with a value, or engine-rendered
effects where the effect renders). Branch-specific lines read the crisis record through the event's saved scopes, which
exist in the preview.

| Act | Lines added |
|---|---|
| `yield` (target) | The concession for **this** crisis, not the four-way list: "Our war support in the war with [issuer] falls by 35" / "We back down in the play; [issuer]'s side wins it" / "Our weapons programme is frozen for 10 years" / "Our forces stand down to Routine, locked for 24 months". Then "The crisis ends" and our credibility −5 (applied by the outcome event, §2.3) |
| `reject` (target) | "The crisis becomes a #v Confrontation#!." Public: "Our refusal is recorded as #R defiance#!: under Nuclear Compellence it licenses a strike on us." |
| `counter_threat` (target) | readiness target → Heightened (if not locked), stage → Confrontation, danger +10 |
| `propose_talks` | "If they accept: both sides stand down to Routine, locked for 24 months, and pledge not to use nuclear weapons on each other; repudiating the pledge later costs 15 credibility and 5 infamy. The war or play goes on." Plus our credibility change on acceptance (±5, by §0.3's rule). "While they consider it, the pressure events stop and danger falls by 15." |
| `accept_standdown` | the same, as happening now |
| `refuse_talks` | "Talks close; the pressure events resume in six weeks." |
| `hold` (issuer) | stage → #R Acute#!; readiness target → High Alert, reached in N weeks (`nd_readiness_step_weeks` × steps), upkeep then X a week (`nd_upkeep_weekly_at_readiness_3`), incident odds up; deadline six weeks from now; "they are pressed again next week" |
| `extend` (issuer) | credibility −3 (#446 key); new deadline six weeks from now |
| `back_down` (issuer) | credibility −15 public / −5 private, −5 more for a called bluff; public: the climb-down modifier and militarist disapproval (applied by the outcome event) |
| `go_public` (issuer) | infamy +5 (engine), relations −15 (engine), stage → Confrontation, new deadline eight weeks, the public stakes |
| `exercise` | the cost modifier (engine), crew strain +5, credibility +3 (issuer), pressure +10 and danger +10 for six weeks |
| `stand_firm` (target, `.5.b`) | "Nothing changes. They will press again in six weeks; their deadline is theirs to act on." |
| `execute_threat` | unchanged, plus the law gate (§1.4) |

### 2.3 The outcome event applies its own consequences

Today `nd_crisis_close` applies both sides' consequences and then fires `nuclear_crisis.6`, whose single option shows
nothing. After this change:

- `nd_crisis_close` records, on **each** party, a pending outcome — `nd_crisis_pending_outcome` (code),
  `nd_crisis_pending_role`, `nd_crisis_pending_public`, `nd_crisis_pending_bluff`, `nd_crisis_pending_opponent`,
  `nd_crisis_pending_concession` (what the target gave up), and a token `nd_crisis_pending_id` = the crisis id — then
  cleans up and fires `.6` with the token set, exactly as the decision events do.
- `.6`'s option calls `nd_crisis_apply_outcome_side`, which applies **this side's** consequences, reading the pending
  record — credibility (number lines), the decaying modifier (engine-rendered), the IG reactions (a line per class, then
  the engine's own lines), lobby appeasement (engine), "no new crisis with [opponent] for 24 months" — then clears the
  pending record.
- The description adds what the other side gave up: "[target]'s war support fell by 35."
- **Two closes before one click.** If `nd_crisis_close` finds a pending record still on a party, it applies that side's
  consequences first (`nd_crisis_flush_pending`) and then writes the new one. The stale `.6` fails its token check and
  is withdrawn (the `nd_crisis_event_valid` pattern). Nothing is lost or applied twice.
- **The concession itself is not deferred.** The target's war-support loss, the play resolved for the other side, the
  programme freeze or the readiness lock still happen inside `nd_crisis_act_yield`, at the moment of yielding; only the
  reputational consequences (credibility, modifiers, IG and lobby reactions, the cooldown) move into `.6`.
- Outcome 9 (a party vanished) fires no event and applies nothing, as today.
- The AI answers `.6` at once, so AI-side consequences land the same week as before.

### 2.4 Checks

- `test_nuclear_deterrence.py` gains: every `nd_crisis_act_*` has at least one number line; every `nd_tt_*` key it
  references exists; `.6`'s option applies consequences and `nd_crisis_close` no longer does (except the flush).
- `silent_variable_audit`, `loc_render_audit`, `script_loc_reference_audit`, `loc_coverage_audit` clean on `/reload`.
- The existing `nd_tt_crisis_opens_$PUBLIC$` keys are stranded in `te_unused_l_english.yml` because
  `organize_loc.py` can't see `$PARAM$`-built keys. The new tooltip replaces them with literal keys; the detection gap
  gets its own issue.

---

## §3 The crisis panel

### 3.1 Only our moves

New scope-free display handlers in `nuclear_deterrence_sguis.txt` (`nd_crisis_we_issued_sgui`,
`nd_crisis_we_are_target_sgui`, `nd_crisis_is_private_sgui`) set row visibility. The widget's rule — no `visible` from an
op-branching `IsShown` — is kept: these are yes/no display handlers, which the rule allows.

| Move | Issuer | Target |
|---|---|---|
| Make the threat public | while private | — |
| Propose a mutual stand-down | yes | yes |
| Hold an exercise they can see | if armed | if armed |
| Concede | — | yes |
| Let the threat go | yes | — |

A visible move that is blocked stays greyed with its failing clause, as now.

### 3.2 New rows

- **If they concede** / **If we concede** — the concession, in the §2.1 wording.
- **Can we carry it out?** / **Can they carry it out?** — Backed / Uncertain / A bluff (custom loc on §1.1's triggers),
  with the reason in the tooltip. The target's version reads the issuer's doctrine from the target's side.
- **Next pressure** — "in N weeks" (`nd_crisis_pressure_interval_weeks − nd_crisis_pressure_weeks`), or "paused while
  talks are open", or "none before the Confrontation stage".
- **Stakes** — our credibility if they concede, if we back down, if it lapses (issuer); the target's version shows what
  standing firm and conceding do to ours.

### 3.3 Tooltips become breakdowns

- **Pressure:** one line per §1.2 component with its number, then the total, then what the total means for the AI:
  "Below 50 they do not concede when pressed; from 70 about half the time; from 85 about two times in three."
- **Danger:** one line per `nd_cd_*` component, the ×0.7 line when it applies, then what it does: incident odds scale
  with it, and at 70 a Confrontation turns Acute.
- **Stage:** what moves *this* crisis to the next stage (from §0.3's rules, filtered by the current stage).

### 3.4 Plain legend

"Our moves. The other side answers through its own decisions. The crisis also ends if the war or play it is about ends."

---

## §4 At Home and the interest-group classes (item 6) — PR 2

### 4.1 Classes

Replaces `nd_ig_class_*` in `nuclear_deterrence_triggers.txt`. Stances are read with vanilla's
`law_stance = { law = law_type:X value > neutral }` (IG scope).

| Class | Who |
|---|---|
| **Professional officers** | `ig_armed_forces` |
| **Business** | `ig_industrialists` |
| **Militarist** | any other IG whose stance on `law_total_war` beats its stance on `law_limited_war` and is at least approve |
| **Restraint** | any other IG whose stance on `law_limited_war` beats its stance on `law_total_war` and is at least approve |
| none | everyone else (a tie, or neither approved) — no nuclear opinion |

**Strength:** approve → mild (the IG's total is capped at ±1); strongly approve → full (±2).

**Lean:** the Armed Forces and Industrialists compute a militarist or restraint lean by the same test. The lean's
doctrine terms are capped at ±1 when mild.

The stance already folds in the leader's ideology, so a fascist-led Intelligentsia turns militarist and a pacifist-led
Armed Forces leans restraint with no special cases. Ideologies with a militarist Rules of War stance today: fascist,
patriotic, vanguardist, jingoist leader, the militarist and imperialist religious outlooks. Restraint: liberal, modern
liberal, market liberal, pacifist, humanitarian, anarchist, the pacifist religious outlook.

### 4.2 Scoring

Existing terms, regrouped per IG (§0.2 of the nuclear design):

| Class | Doctrine terms (need six months' tenure) | Readiness / authority / strain terms |
|---|---|---|
| Militarist | NFU −2, Existential −1, Compellence +1, Warfighting +2 | Routine −1, High Alert +1 |
| Restraint | NFU +2, Existential +1, Flexible −1, Compellence or Warfighting −2 | High Alert −1, Launch on warning −1 |
| Professional | NFU or Warfighting −1, Flexible +1 — *replaced* by the lean's doctrine terms under a lean | Routine with a plausible attacker −1, Heightened +1, High Alert with strain ≥ 50 −1 |
| Business | none — the lean's doctrine terms under a lean | High Alert held 3+ months −1, a crisis at Confrontation or beyond −1 |

The total is capped at ±2 (±1 for a mild class) and maps onto the existing `nd_posture_approval_*` bands.

### 4.3 One writer

`nd_refresh_domestic_stance` (monthly, unchanged call site) runs `every_interest_group` and stores, on the IG:
`nd_ig_class` (1 militarist, 2 restraint, 3 professional, 4 business), `nd_ig_lean` (0/1/2), `nd_ig_strength` (1 mild,
2 full), `nd_ig_term_doctrine`, `nd_ig_term_readiness`, `nd_ig_term_authority`, `nd_ig_term_strain`,
`nd_ig_term_business`, and `nd_ig_stance` (the capped total); then applies the band from `nd_ig_stance` as today. An IG
with no class has its variables removed and its band cleared. The four country-level `nd_stance_*` variables go.

**Fallback if IG-scope variables fail in game:** a variable map on the country keyed by the IG
(`add_to_variable_map`), read by the display handlers. The class triggers and the band application do not depend on the
storage.

### 4.4 Display

`widget_je_nuclear_posture`'s At Home section becomes a `dynamicgridbox` over
`JournalEntry.GetCountry.AccessActiveInterestGroups`, one row per IG with `nd_ig_class` set:

- **Name** — `InterestGroup.GetNameNoFormatting`.
- **Class** — custom loc on the IG scope: "Officers", "Officers, hawkish", "Officers, restrained", "Business",
  "Business, hawkish", "Business, restrained", "Militarist (mild)", "Militarist", "Restraint (mild)", "Restraint".
- **Approval** — `nd_ig_stance`, signed and coloured.
- **Tooltip** — each non-zero term with its reason ("Doctrine: Existential Deterrence −1"), the cap if it bit, and
  "the same figure appears in this group's approval breakdown".
- **Footer** — "Reviewed monthly." Plus, while doctrine tenure is under six months, "Doctrine opinions start in N months."

### 4.5 Knock-on

The crisis rewards (`nd_reward_hawks`, `nd_reward_doves`) and the incident events that pay "militarists" or "doves" call
the class triggers, so they follow the new classes. **Hawks:** militarists, the Armed Forces unless they lean restraint,
the Industrialists when they lean militarist. **Doves:** restraint groups, and either of the two when it leans restraint.
Two new triggers, `nd_ig_is_hawk` and `nd_ig_is_dove`, carry this; the reward and incident sites switch to them.

---

## Testing

- **Unit** (`test_nuclear_deterrence.py`): §2.4's checks; the §1.2 components sum to the total (parse
  `nd_yield_pressure_value` and assert it is exactly the component list); every §3 row's loc key and display handler
  exists; every class and lean has its custom-loc branch.
- **Reload**: the fast `?mod_only=true&audits_only=true` path on a second server port from the worktree
  (`docs/guides/python_tools.md`, #445); the `warnings` array clean.
- **In game** (added to `nuclear_crisis_design.md` §0.9):
  1. The ultimatum's confirmation box shows infamy, relations, the dispute and its concession, follow-through, the factors,
     the stakes and "follow it in the journal entry"; `error.log` stays quiet while it is open.
  2. The Canada case: Existential Deterrence in a minor war reads "A bluff", and the panel's pressure shows −25 for it.
  3. Every crisis event's options show numbers.
  4. "The Demand Is Met" shows the credibility gain and the modifier in its option, and the target's lost war support in
     its text; answering it applies them once.
  5. The issuer does not see Concede; a public crisis does not offer Go public.
  6. At Home lists the IGs with the numbers their approval breakdowns show; a fascist-led Intelligentsia is militarist.
  7. A country under Limited War cannot "carry out the threat".

## Out of scope

- Item 4 (overlord umbrella) and item 7 (Recessed readiness, Automatic retaliation authority): separate designs.
- A free-form offer builder, the genuine-warning variant, espionage on estimates (§0.7 of the nuclear design).
- The `organize_loc.py` `$PARAM$` detection gap: its own issue.
