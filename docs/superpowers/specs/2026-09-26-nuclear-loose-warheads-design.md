# Nuclear custody, part two: denying the bomb, foreign reaction, the Budapest path, loose warheads — design

## Context

`docs/systems/nuclear_crisis_design.md` §0.10 is the roadmap agreed with the owner on 2026-09-25/26. PR #467 built
step 2 (custody transfer: the arsenal ledger, the settlement) and the first event of step 3 ("Who Holds the Button?").
This document is the rest, as built:

- **Step 3, the rest.** "Deny Them the Bomb" when the loyalists are losing, and the foreign-reaction event (back a side,
  offer to secure the arsenal, stay out).
- **Step 4, the Budapest path.** Great powers press winning secessionists to trade their share for a guarantee, using
  the existing `nuclear_disarmament` and `nuclear_guarantee` articles.
- **Step 5, loose warheads.** Detonation through `nuclear_industrial_strike` in the terrorism era, the attribution roll
  (confirmed / shortlist / unknown), and recovery (a covert operation, a treaty article, a UN convention). Buying warheads
  (its phase 2) is out of scope.

Baseline: `main` at `b2f72089` (#467 merged). Built while the owner was away: every choice not already ruled in §0.10 is
listed under **Calls made without the owner** at the end. Nothing here has run in a game; the checklist is
`nuclear_crisis_design.md` §0.9 items 51–59.

## Owner rulings this rests on (§0.10)

| Ruling | Source |
|---|---|
| The loose pool is a world count plus a per-origin count (`nd_ar_loose` on the ledger record, passing to the successor's record when the origin dies) | 2026-09-25 |
| Detonation reuses `nuclear_industrial_strike`, gated by the `terrorism_and_anti_terrorism` era, drawing from the social-tensions terror pool | 2026-09-25 |
| Attribution keeps the truth (per-origin counts) apart from what the victim learns: confirmed / shortlist / unknown, with odds that rise with few candidate origins, the victim's nuclear expertise, an origin that has tested openly (`nuclear_power`) and a covert network in the origin | 2026-09-25 |
| Blame means negligence: compensation, inspections, custody cooperation | 2026-09-25 |
| Recovery: a covert operation, a treaty article paying an origin to secure its stock, a UN physical-protection convention | 2026-09-25 |
| Budapest: winning secessionists keep their share; great powers press them to trade it for a guarantee with the existing articles; the upkeep of warheads one cannot build is the pressure | 2026-09-25 |

## 0. A fix to #467 found on the way

`nd_country_monthly_cleanup` lifted the "Pull them back" lock (`nd_cw_withdrawn`) once `any_civil_war` found nothing.
That iterator walks the civil wars still **brewing** (a movement's `civil_war_progress`; vanilla's journal entries test
`civil_war_progress >= 0.75`), not a war that has broken out, so the lock could lift the month after the outbreak.
`nd_in_civil_war` now reads the rebel country (`civil_war_origin_country` + `is_revolutionary` / `is_secessionist`), and
every "is our civil war still on" test here uses it.

## 1. Step 3, the rest

### 1.1 "Deny Them the Bomb" (`nuclear_custody.5`)

A revolution's winner inherits whatever the government still holds. A secession's winner does not take the government's
arsenal, so this event is for revolutions only.

- **Who and when.** `nd_cw_monthly_check`, from `nd_country_monthly_cleanup`: an armed original country with a live
  revolutionary rebel, losing to it (`nd_is_losing_war_to`: 25 % occupied, or losing its battles), not yet asked in this
  civil war (`nd_cw_deny_asked`, forgotten with the custodian once `nd_in_civil_war` is false).
- **The roll** (`immediate`): a hasty dismantling loses `stock × nd_cw_outbreak_loss_rate`, stochastically rounded.

| Option | Effect |
|---|---|
| **Take them apart now** | the rolled loss goes to the pool against our line; the rest are dismantled (`nd_cw_dismantle_as`: stockpile 0, `nuclear_power` off, relations +10 with everyone) |
| **Let [custodian] take them apart** (only with a custodian still alive, armed and at peace with us) | dismantled with nothing lost; relations +10 with everyone, +15 more with the custodian |
| **Keep them** (default) | nothing now; the tooltip says what a winning revolution would inherit |

AI: keep 3 (+2 aggressive); take apart 2 (+3 cautious, +3 at 50 % occupation); supervised 8.

### 1.2 Foreign reaction (`nuclear_custody.6`, `.7`, `.8`)

- **Who.** `nd_cw_notify_world`, from the outbreak of an armed country's civil war: every power believed armed that is
  a major power or borders the origin, party to neither side (`nd_cw_would_watch`). The pair is stored on the observer
  for a month (`nd_cwr_origin`, `nd_cwr_rebel`), and the event arrives a week later, once `.1` has been answered.
- **`.6` "A Nuclear Power Divided"**: **back the government** or **back the rebels** (relations ±20; the backed side's
  war support in the civil war +5), **offer to secure their arsenal** (armed, not hostile, no offer pending or accepted),
  or **stay out** (default). AI: backs the government when protective / genial / loyal, in its bloc, or cordial; backs
  the rebels when rival or hostile; offers when the government holds 5+ warheads (+ as a great power).
- **`.7` "An Offer to Secure Our Arsenal"** (government): accept — the helper becomes our custodian (`nd_cw_custodian`),
  our custody is secured for the civil war, relations +10; decline — relations −5. AI accepts unless rival, hostile or wary.
- **`.8`** tells the helper.

### 1.3 Secured custody

`nd_custody_is_secured` (country): a civil-war custodian, `nd_loose_inspected` (twenty years after opening custody to
inspection), a `nuclear_security_assistance` article as its target, or the UN convention's member modifier.
`nd_ledger_refresh` copies it to the record (`nd_ar_secured`). Both loss rates halve under it, after their clamp.

## 2. Step 4, the Budapest path

- **Who.** `nd_bp_open` from `te_civil_war_on_secession_end`: a secession that won (alive) holding warheads.
- **`.10` "A New Nuclear State"** to every great power believed armed and not at war with it, a week later (the state
  stored on the power for a month): **press them** — joins `nd_bp_guarantors`; the first to press schedules `.11` a
  month out — or **leave it** (default). AI presses (6) unless hostile to the new state (factor 0: a hostile power uses
  the ordinary article); friendly powers lean to leave it (+6).
- **`.11` "The Budapest Offer"** (the new state): the lead guarantor is the largest economy among those still able
  (`nd_bp_guarantor_valid`).
  - **Trade them for guarantees**: `create_treaty` in force, 10-year binding: with the lead, `nuclear_disarmament`
    (source = the new state, target = the lead) and `nuclear_guarantee`; with each other presser, `nuclear_guarantee`
    alone. Each is gated by a `can_create_treaty` trigger kept identical to its effect (a test compares them). If the
    lead's disarmament cannot be created (it wants the disarming state's `nuclear_weapons` tech), the lead signs the
    guarantee alone. The warheads are zeroed directly after the treaties as well. Relations +20 with each.
  - **Keep them** (default): relations −20 with each; `nd_bp_refused` for ten years adds 0.25 to the AI's evaluation
    chance of demanding `nuclear_disarmament` from it.
  - AI: trade 3 (+4 without `nuclear_weapons`, +2 with 3 or fewer, +2 with two or more guarantors); keep 3 (+4 facing an
    armed rival or an armed hostile neighbour, +2 aggressive).
- **`.12`** tells each guarantor.

## 3. Step 5, loose warheads

### 3.1 The plot (`nuclear_loose.1`, hidden)

Weight 3 in `on_yearly_events`' random_events (`social_tensions_on_actions.txt`), beside the domestic terror attack.
`nd_loose_plot_possible`: nuclear rule; the pool holds a warhead; no world cooldown; `terrorism_and_anti_terrorism`; not
decentralized; a populous incorporated state; the terror attack's unrest gate (radicals ≥ 10 %, at war, or a radical
movement ≥ 25).

1. **A device?** `nd_loose_plot_chance` = 20 % per warhead in the pool, max 80.
2. **Whose?** `random_in_global_list` over `nd_arsenal_records`, weighted by `nd_ar_loose`, among lines whose owner is
   alive and is not the victim (`nd_loose_line_usable`).
3. `nd_loose_surface`: the world cooldown (365 days) and `nd_loose_device_surfaced` (permanent) are set only now. The
   warhead leaves the pool (world −1, line −1). The victim is marked `nd_loose_was_target` (for the UN lean).
4. **Seized?** `nd_loose_foil_chance` = 10 + 5 per intelligence-ministry level + 15 with `nuclear_weapons`, max 75.

### 3.2 Seizure (`.3`) and detonation (`.2`, `.5`)

- **Seized**: nothing detonates; the attribution gets +20.
- **Detonated**: `random_scope_state` among populous incorporated states, weighted by
  `nuclear_industrial_strike_target_score`, gets `nuclear_industrial_strike` with no `scope:attacking_country` (no
  `nuked_by_country`; the strike's own war-support loss still applies to any war the victim is in). Every other human
  country gets `.5`.
- Either way, `.4` reports the investigation a month later.

### 3.3 Attribution (`nd_loose_attribute`, rolled at once)

`nd_loose_confirm_chance` = 10 + 30 (one candidate line) / 15 (two) + `nd_loose_expertise` (15 `nuclear_weapons`, 10
armed) + 15 (origin has `nuclear_power`) + `nd_loose_network_part` (15 / 25 for a covert network in the origin at
intelligence tier 1 / 2, read from the stored `iw_net_intel_tier`) + 20 (seized), max 90. Otherwise
`nd_loose_unknown_share` = 60 − expertise − network part (10–90) % stays unknown, and the rest gets a shortlist: the true
origin and up to two decoys (another line's owner first, then countries believed armed) in random order
(`nd_loose_suspect_1..3`). A shortlist of one names the origin outright. Candidates are counted as the pick saw them.

**Victim (`.4`):** hold a confirmed origin to account (relations −30, the demand); name a shortlist in public (relations
−25 each, `.7` to each; AI only under an aggressive ruler); ask each suspect privately (`.6`'s request variant); blame a
rival when nothing is known (relations −30, loyalists); or say nothing (default).

### 3.4 The reckoning (`.6`, `.8`)

| Option | Effect |
|---|---|
| **Pay** (the full demand only) | the sum fixed at sending: a tenth of the payer's yearly revenue, capped at a tenth of the victim's GDP (the reparations formula); relations +20 |
| **Let their inspectors in** | secured custody for twenty years (`nd_loose_inspected`), `nd_loose_inspections` (−5 legitimacy, decaying over ten), a first search with 50 % to recover one of our loose warheads; relations +10 |
| **It was not ours** (default) | full demand: relations −40, infamy +5; request: relations −10 |

### 3.5 Recovery

A recovered warhead is destroyed and leaves the pool (`nd_loose_recover_from_line`); `nd_loose_tell_recovery` tells
whoever should hear (`.9`).

1. **Inspection's first search** (above).
2. **Covert operation "Secure Loose Material"** (`covert_secure_material_action`, code 13, **mild**, military defence;
   also needs the nuclear rule): a target with a loose line, which is also its `requirement_to_maintain`. Its own block in
   `covert_ops_apply_all_phase_effects`: once established, a monthly `covert_secure_material_chance` (3 ×
   `covert_op_effect_mult`: 3 % / 6 % / up to 9.6 %). The operator hears; the target never does. AI: major power or
   above, against any target with a loose line (score 5, +5 neighbour).
3. **Treaty article `nuclear_security_assistance`** (Nunn–Lugar): directed; source = the armed provider (pays the
   influence upkeep, 100), target = a country armed or with a loose line (carries the leverage). The target's custody is
   secured and `nd_loose_monthly` gives it 6 % a month. AI offers and requests it where a line is loose.
4. **UN Convention on the Physical Protection of Nuclear Material** (§3.6): 3 % a month for a party, and secured custody.

### 3.6 The UN convention

Topic `physical_protection`, agency `un_agency_cppnm`, chamber op 17, proposer `un_events.23`, ledger reason 1231; built
on the law of the sea's template at every site but the regime modifier. Agenda business, open only under the nuclear
rule and once warheads have gone loose (the pool holds one, or `nd_loose_device_surfaced`), at authority 30; offered to
members with `nuclear_weapons`. The country-scoped member modifier `un_physical_protection_modifier` carries a cosmetic
prestige line only (E-scaled); what a party gains is the check in `nd_custody_is_secured` and `nd_loose_monthly`. The
chamber row is hidden under the disabled nuclear rule (`un_chamber_nuclear_rule_sgui`). AI lean: targeted +30, armed
+10, terrorism era +10, own line loose −15, isolationism −20.

### 3.7 The panel

The posture panel's **Unaccounted for** row (`nd_loose_sgui`), while our line has warheads missing; the world count in
its tooltip.

## 4. Tests, docs

- `test_nuclear_deterrence.py`: `TestCustodyLosingAndWatching`, `TestBudapestPath`, `TestLooseWarheads`,
  `TestLooseRecovery`, and the lock fix in `TestCustody`; the new files join the fired-event and loc checks, which now
  also count an on_action's weighted `random_events` entry as firing an event.
- `test_covert_op_registry.py`: the `OPS` row and `ACTS_WITHOUT_MODIFIER`. `test_un_membership.py`: ten conventions.
- Docs: `nuclear_crisis_design.md` §0.1, §0.9 (51–59), §0.10; `mod_systems.md` § Nuclear Weapons and § Covert Warfare;
  `journal_entry_systems.md` and `un_redesign_design.md` (the convention); README (the covert count).

## Calls made without the owner (confirm)

Everything below was decided while building; none of it is in §0.10's rulings.

- **Deny Them the Bomb** is for revolutions only (a secession's winner does not inherit the government's arsenal); it
  fires once per civil war when `nd_is_losing_war_to` holds; a hasty dismantling loses the outbreak's (doubled) loss
  rate; the supervised option needs a custodian accepted from the foreign-reaction offer.
- **Foreign reaction**: observers are powers believed armed that are major powers or border the origin; "backing" is
  relations ±20 and +5 war support in the civil war — no one joins the war; "securing" makes the helper a custodian that
  halves the loss rate for the war, and only the first offer counts.
- **Secured custody** halves the loss rate, and has four sources (custodian, inspection, the article, the convention).
- **Budapest**: only great powers believed armed press; the lead guarantor (who holds the disarmament and pays its 200
  influence upkeep) is the largest economy among them; treaties are 10-year binding; the warheads are also zeroed
  directly; refusing costs −20 relations and ten years of readier AI disarmament demands.
- **Plot odds**: pool weight 3; 20 % per warhead, max 80; a year-long world cooldown set only when a device exists; a
  victim's own lost warheads are never turned on it; the target city is weighted by the strike score.
- **Seizure** (not in the rulings): 10 % + 5 per intelligence-ministry level + 15 with `nuclear_weapons`, max 75; a
  seized device attributes more easily (+20).
- **Attribution numbers** (§3.3), including that a shortlist names decoys from other lines first and then any country
  believed armed, and that a one-name shortlist becomes a confirmation.
- **The victim's options** and that the AI names suspects in public only under an aggressive ruler.
- **Compensation** uses the decolonization reparations formula; **inspection** is twenty years of secured custody, −5
  legitimacy decaying over ten, and a 50 % first search; **denial** of a confirmed attribution costs +5 infamy.
- **Covert operation** tier mild, military defence axis, 3 × the phase/priority multiplier per month, operator told and
  target not, lens icon copied from nuclear sabotage.
- **Article**: provider must be armed, pays 100 influence; 6 % a month.
- **Convention**: agenda business (not a docket situation); open once warheads have gone loose, permanently after the
  first device surfaces; 3 % a month; the lean weights above; no regime modifier.
- **The panel row** shows only our own line's count; the world count is in its tooltip.
