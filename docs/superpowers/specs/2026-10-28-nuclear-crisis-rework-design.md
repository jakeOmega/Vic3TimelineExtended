# Nuclear Crisis Rework: Survivability, Launch Authority, Accidental Risk and Crisis Subjects — Design

> **Status: phase 1 built (2026-10-28, branch `feat/nuclear-rework-p1`; plan `docs/superpowers/plans/2026-10-28-nuclear-crisis-rework-phase1.md`); phases 2–4 designed, not built.** Owner answers to §14.1 (confirmed) and §14.2 (launch authority is public) are in §14. Baseline `main` at c760baf. The owner's calls from the 2026-10-28 review are §1; everything else is a proposal, and every number is a first tuning value. Engine facts the design rests on but nobody has verified are §12, each with a fallback. Per the owner they are checked in game while building, not before it.
> Read first: [`docs/systems/nuclear_crisis_design.md`](../../systems/nuclear_crisis_design.md) §0, what shipped. This doc changes its §0.2–§0.5. When a phase ships, update §0 there, chapter 14 of the player guide and `docs/testing/nuclear-playtest.md`.

## 0. Why

The 2026-10-28 review of the shipped posture, crisis and incident systems found six problems.

1. **Delegation and Launch on Warning only cost.** Nothing in pressure, danger or retaliation reads launch authority 2 or 3. Their display modifiers (`nd_authority_terms_2`/`_3`, `common/static_modifiers/nuclear_deterrence_modifiers.txt`) list only risks: unordered launches, −10 to the chance of a halt, +3% custody loss. Central Authorization is strictly better. Once Mainframe Computers exist, Automatic Retaliation is both safer than Launch on Warning and the only authority that pays: `nd_yp_answer_value` counts it as survivable.
2. **Survivability is perception only.** A strike never touches the victim's arsenal. `nuclear_first_strike` (`common/scripted_effects/extra_effects.txt:546`) spends only the attacker's warhead, so every warhead is always there for the answer. Survivability's one payoff is the target's pressure term, a step at 50: −10 below, −25 at or above (`common/script_values/nuclear_deterrence_values.txt:745`). The AI also reads it at thresholds of 30, 40 and 50. The issuer's own survivability is read nowhere.
3. **Accidental risk exists on paper and is absent in play.**
   - Central Authorization cannot launch by accident. A warning goes to the government, whose order (`nuclear_incident.1.c`, `events/nuclear_incident_events.txt:146`) needs a war with the suspect and the deliberate-strike gates.
   - The AI pairs every risky authority with safeguards. `nd_ai_review_posture`'s investment block (`common/scripted_effects/nuclear_deterrence_effects.txt:1446`) sets one level, +1 for Delegation or Launch on Warning and +1 at High Alert, which holds the chance of a halt at or near its 97% ceiling. Under the AI's own rules an unordered launch comes to 0.02% a year (Delegation, Heightened, at peace), 0.6% a year (Delegation, at war with an armed enemy), 1.7% a year (Launch on Warning, the same war) and about 0.7% a week (Launch on Warning, an Acute crisis at danger 75+).
   - A war adds no incident exposure. The crisis surcharge (`nd_incident_crisis_weekly_permille`, `nuclear_deterrence_values.txt:363`) reads crisis danger only, so a conventional war with an armed power that doesn't threaten its existence carries almost no nuclear risk.
   - The other corner is reckless. Launch on Warning with no safeguards in an Acute crisis runs 6% a week, 64% over eight weeks for two such sides. The whole spread lies in the authority and safeguards choice, and the safe corner costs nothing.

   The owner (2026-10-28): this is wrong for gameplay, because it strips the risk from conflicts with nuclear powers short of their survival, and wrong as a message, because nuclear tensions were dangerous.
4. **The victim can't tell an accident from an attack, then or later.** The struck country gets `nuclear_weapon_events.1`, "A City Erased", either way; only the launcher learns the launch was unordered (`nuclear_incident.4`).
5. **Crisis subjects are narrow and two concessions are off** (`nd_crisis_classify_dispute`, `common/scripted_effects/nuclear_crisis_effects.txt:320`):
   - War: the yielder loses 35 war support (`nd_crisis_concede_war`, `:1680`). That is neither de-escalation nor surrender, only a push toward capitulation.
   - Play: `resolve_play_for` hands the issuer's side the play whatever it demanded. Pressure has no term for the size of the demand, and a side can make several primary demands.
   - Protégé: a treaty guarantee or the umbrella counts; an unarmed co-belligerent (one that joined through a sway, say) does not.
   - Proliferation counts an armed rival's continuing warhead program, so one crisis can freeze a rival's arsenal for ten years.
   - Missing: a peacetime nuclear exchange (so "Honor" after a peacetime strike on a protégé opens nothing, because `nd_beneficiary_threatened_by`, `common/scripted_triggers/nuclear_deterrence_triggers.txt:784`, needs a war or a play), forward deployment, claims, covert operations, missile defense and orbital weapons. No settlement trades one concession for another.
6. **No range.** Any armed country can strike any enemy state from its first bomb.

## 1. Owner calls (2026-10-28)

| # | Call |
|---|---|
| 1 | Risk is real for every posture. No posture or investment makes nuclear tension safe |
| 2 | Calibrate to the Cold War: to an order of magnitude, our Cold War had a 50% chance of a nuclear war of some scale and perhaps 25% of a huge exchange. A more multipolar world runs higher, having more opportunities |
| 3 | Survivability is measured against the other side's arsenal, and continuously: no cliff |
| 4 | Survivability's effect on danger is small and secondary: linear below 50, about +10 at 0 |
| 5 | Delegation and Launch on Warning get a payoff. The highest survivability may need both hardening and a fast authority |
| 6 | Safeguards trim that payoff, but Delegation with safeguards must still beat Central with none: safeguards cost money |
| 7 | Counterforce and decapitation, scaled by the size of the attack: one warhead can't disarm or decapitate a large arsenal |
| 8 | A strike can commit several warheads: a new action, or the strike actions reworked into the panel, where the player says what the strike attempts |
| 9 | The war concession follows the Suez model: the target drops its war goals against the issuer, plus a smaller war-support hit |
| 10 | The play concession counts every primary demand, since a side can make several at extra cost |
| 11 | An unarmed co-belligerent counts as covered for the length of the war |
| 12 | A launcher may claim an accident, some claims are false, and the truth comes out later |
| 13 | Deployment uses neighbors as the stand-in for range, unless a feasible range mechanism exists. §7 proposes one |
| 14 | New disputes: a peacetime exchange, deployment, claims, covert operations, missile defense, orbital weapons. Settlements can trade concessions |
| 15 | Removing war goals from a war, and removing a play's opening goal, should work: vanilla removes goals in some cases. The engine probes go in this doc, not ahead of it |

## 2. Risk targets

### 2.1 The anchor

Owner call 2 gives a Cold War–like world, with two great-power arsenals in rivalry, three to five smaller ones and about 45 years, a 50% chance of some nuclear use and 25% of a large exchange. That is a world hazard of about 1.5% a year for any use and 0.6% a year for a large exchange. Split by where the historical danger came from (first estimates):

| Source | Historical cases | Share of the risk | Rate to calibrate |
|---|---|---|---|
| Acute crises between armed powers | Berlin 1961, Cuba 1962, Yom Kippur 1973, Able Archer 1983 | about half | 6–10% chance of some use per Acute crisis, deliberate use included |
| Wars involving an armed power | Korea, the Sino-Soviet border war of 1969, Vietnam, Kargil 1999 | about a third | at war with another armed power: 10–20% a war-year. Against an unarmed enemy whose war doesn't threaten it: 0.5–1% a war-year |
| Peacetime false alarms and accidents | Goldsboro 1961, the 1979 training tape, the 1980 chip, Petrov 1983, the Norwegian rocket 1995 | the rest | 0.05–0.1% an unordered launch per armed-rival pair-year at Heightened or above |
| Escalation after a first use | | | about half of all first uses grow into a large exchange |

Near misses, meaning a launch halted at the last moment or a recalled order, should be several times as common as unheld launches: 10–20 over such a world's 45 years, so a player in a nuclear rivalry sees a few.

A **large exchange**, for the observer report: each side lands at least three strategic warheads, or a quarter of the smaller arsenal, whichever is fewer.

### 2.2 Multipolar worlds

Every rate above is per crisis, per armed pair or per war, so a world with more armed rivals runs a higher total by itself: four mutually hostile armed powers make six pairs. There is no world-level multiplier.

### 2.3 Bands per posture

No posture is safe, and recklessness isn't free. Chance of an unordered or mistaken launch by either side during an eight-week Acute crisis at danger 75+, both sides at High Alert, reliability where the safeguards put it, no strain:

| Posture of each side | Shipped | Target |
|---|---|---|
| Central, safeguards 3 | 0 | 2–3% |
| Central, safeguards 0 | 0 | 4–6% |
| Delegation, safeguards 3 | 1% | 3–5% |
| Launch on Warning, safeguards 3 | 5% | 8–12% |
| Launch on Warning, safeguards 0 | 64% | 20–30% |

Blended over the AI's postures, plus deliberate use, it should come to §2.1's 6–10% per Acute crisis. Owner call 6 is the Delegation row against the Central-with-none row: comparable risk, better deterrence (§4).

### 2.4 How it is measured

- `scripts/analysis/nuclear_incident_rates.py` gains the in-crisis and in-war cases (§11), so a retune is checked against §2.3 offline.
- `scripts/analysis/nuclear_observer_report.py` gains uses per Acute crisis, per armed pair-year and per war-year, near misses, claims and exchange size, so observer runs are checked against §2.1.

## 3. Second-strike security

### 3.1 Survivability stays; its ceiling drops

`nd_survivability` keeps its climb with hardening, its decay without, and the readiness factors of `nd_effective_survivability`. The technology ceiling, `nd_survivability_cap`, keeps its parts but tops out at 80 instead of 95. The last stretch toward full security then has to come from a fast authority (§4), as owner call 5 asks.

### 3.2 Survivors against a given enemy

For country X facing enemy Y:

- **Exposed warheads:** stockpile(X) × (1 − effective survivability(X) ÷ 100).
- **Exchange ratio K(Y):** how many of X's exposed warheads one landed counterforce warhead destroys. 1.0 to start, +0.5 with ICBMs, +0.5 with Precision Guided Munitions (era 8).
- **Launch credit(X):** the share of the warheads a counterforce strike would destroy that get away first (§4.1).
- **Survivors(X against Y)** = stockpile(X) − min(exposed(X), K(Y) × stockpile(Y)) × (1 − credit(X)).

X's own stockpile is the true one; Y's is X's belief (`nd_believed_stockpile`), so the measure leaks nothing. It is worked out in `nd_crisis_refresh_figures` (weekly, for crisis pairs only), and in the AI's posture review against its most dangerous armed rival. Arsenals are small (an AI great power wants about 5–20 warheads, `nuclear_ai_desired_stockpile`), so every figure here is in single and double digits.

### 3.3 Where it is read

- **Can they answer in kind?** (`nd_yp_answer_value`). Unarmed +20, as now. Armed: −25 × min(1, survivors(target against issuer) ÷ 3); three warheads is a full retaliation in `nuclear_weapon_events.1`. A target under Central Authorization that the issuer could decapitate (§6.3: the issuer's believed stockpile exceeds the target's redundancy R) counts its survivors at three quarters. The term is continuous, and it replaces both the line at 50 and Automatic Retaliation's blanket −25.
- **Can the issuer afford it?** A new pressure part, `nd_yp_issuer_exposure`, against an armed target only: 0 while survivors(issuer against target) is 3 or more, falling linearly to −15 at 0. A threat from a force the target could disarm first is a weaker threat.
- **Danger** (owner call 4). A new part, `nd_cd_vulnerability`: (50 − effective survivability) ÷ 5 for the more vulnerable armed party, so +10 at 0 and nothing from 50. It is absolute, not relative to the enemy: a secondary effect.
- **The AI's thresholds.** The readers that draw a line at 50, 40 or 30 (the counter-threat weight `nuclear_crisis.1.c`, the walk-away weight `.20.c`, High Alert in an Acute crisis, the authority choice) read survivors instead: under 3 is vulnerable.

Counterforce in the exchange itself is §6.

## 4. Launch authority and safeguards

### 4.1 What each authority does

| Authority | Counterforce credit | Decapitation (§6.3) | Accident exposure |
|---|---|---|---|
| Central | 0 | can be decapitated | warnings go to the government, which may order a launch under attack (§5.3) |
| Delegation | 0.25 | immune | cut-off commanders (`.20`); warnings in a war with the suspect |
| Launch on Warning | 0.6 | immune | warnings and cut-off commanders, in peace too |
| Automatic Retaliation | 0: it answers with whatever survives | immune, and the answer is certain | weapons accidents read as an attack |

Through §3.3, credit makes a vulnerable force under Launch on Warning count as more secure. The choice becomes harden (slow, costly, safe) or launch on warning (instant, cheap, risky). Automatic Retaliation loses its blanket −25. It keeps the certainty of its answer and immunity to decapitation, which §3.3's three-quarters rule turns into pressure.

### 4.2 Safeguards trim the credit

Each safeguards level takes 0.05 off the credit of Delegation (0.25, down to 0.10 at level 3) and Launch on Warning (0.6, down to 0.45): a launch that can be halted is a slower launch. Safeguards keep their price, 2 upkeep units a level. Owner call 6 holds: Delegation at safeguards 3 has a 0.10 credit and immunity to decapitation, against nothing for Central at safeguards 0, at comparable risk (§2.3, 3–5% against 4–6%).

### 4.3 The chance of a halt

`nd_hold_chance` (`nuclear_deterrence_values.txt:477`) gains four terms:

- **A ceiling by context**, replacing the flat 97: 97 at peace with no crisis, 92 in a Warning or Confrontation, 85 in an Acute crisis or a war. No investment takes the risk away (owner call 1).
- **The suspect's posture:** +20 when its forces are Recessed, since it cannot launch; −5 when it is at High Alert.
- **A hotline:** +10 while the crisis's talks are open.
- **Our own vulnerability:** −(50 − effective survivability) ÷ 5, at most −10, the shape of the danger term. Commanders fear losing the force.

### 4.4 The AI's posture

- **Safeguards are no longer automatic.** Start at 1. Add 1 for a cautious ruler, 1 for a restraint-class government (the At Home classes), and 1 under Delegation or Launch on Warning. Take 1 off for a militarist regime or Warfighting (safeguards slow the answer, §4.2), and 1 in a budget deficit. Clamp to 0–3.
- **Authority weighs the new payoffs.** Launch on Warning or Delegation when survivors against its main rival are under 3 and hardening won't close the gap within a few years. Automatic Retaliation when available and not militarist. Back to Central once the threat has passed; today only a cautious ruler moves it back.

## 5. Accidental escalation

### 5.1 War exposure

A war with an enemy believed armed adds the crisis surcharge as if danger stood in band 2 (50–74). It is band 3 when either side holds goals on the other's incorporated states, either side is losing (`nd_is_losing_war_to`), or a nuclear weapon has landed in the war. Alongside a crisis, the higher band applies. Like the crisis part, it feeds only the misreading families (warning, exercise, cut-off commander). §2.1's war rates set its size.

### 5.2 The chance of a halt

See §4.3.

### 5.3 Central Authorization: the decision under a warning

Today "Give the launch order" (`nuclear_incident.1.c`) needs a war with the suspect and the doctrine's permission (owner ruling of 2026-09-26, `nuclear_crisis_design.md` §0.7). A warning that reads as an incoming strategic attack is the case every doctrine but No First Use was written for. Proposal: in a war with the suspect, or an Acute crisis against it, the launch-under-attack order passes the doctrine gate under every doctrine except No First Use. The pledge, Rules of War and assembled-forces gates stay. If the warning was false, the launch is a first use and pays as one.

The AI orders it with a weight that rises with its vulnerability (survivors under 3), an aggressive ruler, strain and an Acute crisis, and falls with a cautious ruler, a second source of warning (Recon Satellites, Satellite Communications) and open talks. This is where Central's risk in §2.3 comes from.

**This reverses part of the 2026-09-26 ruling. Owner to confirm (§14).**

### 5.4 The victim's dilemma

- **The claim** (owner call 12). After any strategic strike, the launcher may tell the victim "It was unauthorized" over the hotline. After an unordered launch it is true; after a deliberate one it is a lie. A human chooses freely. The AI lies with a small chance: after a deliberate single-warhead strike on an armed target, more often with an aggressive ruler and a low taboo.
- **The victim's answer.** `nuclear_weapon_events.1` carries the claim in its text and a new option: accept it, holding back or answering with one warhead, and demand reparations (the formula `nuclear_loose.6` uses).
- **Belief.** An AI victim believes the claim with a chance of 40, + relations ÷ 4, +20 if only one warhead landed (a deliberate first strike is usually larger), −20 if the launcher is its Acute-crisis opponent, −30 for each false claim of the launcher's already exposed (`nd_false_claims`), clamped to 5–90.
- **The truth.** Six to eighteen months later, sooner with an established covert network, the victim learns what happened: "It Was an Accident" or "It Was No Accident". This also comes when no claim was made. An exposed lie costs −20 credibility, infamy scaled by the taboo, −50 relations with the victim and a mark in `nd_false_claims`. A true claim that was rejected opens a reconciliation option. `trigger_event` takes one literal delay, so the delay is a `random_list` of literal branches, as `nd_crisis_send_event_in_transit` does.

## 6. Strikes: the planner, counterforce and decapitation

### 6.1 The strike planner

A Strike section in the Nuclear Weapons panel (owner call 8). The player picks an enemy (a war or an open exchange), a mission and a size (a stepper from 1 to the warheads available), then orders it. The missions:

| Mission | Aimed at | Notes |
|---|---|---|
| Cities | the enemy's most populous reachable states, one warhead each | today's strategic strike |
| Forces | the enemy's arsenal (§6.2) | a quarter of a city strike's casualties, in states with a Military Base or Barracks, else the capital region |
| Leadership | the capital state (§6.3) | |

An order runs the existing gates once (doctrine, pledge, Rules of War, assembled forces) and goes through `nd_launch_or_intercept`'s dispatch. The AI orders through the same effect. Tactical strikes (`tactical_nuke_diplo_action`) stay as they are.

Open: hand-picking which cities to strike needs either the map, through the diplomatic action's `state_selection`, or a list of states in the panel. If the list proves impractical, keep `nuke_diplo_action` for one chosen city and use the planner for salvos.

### 6.2 Counterforce

Each warhead lands with the existing chance (delivery minus defense). Destroyed = min(exposed(victim), K × landed) × (1 − credit(victim)), stochastically rounded, and those warheads leave the victim's stockpile. The warheads Launch on Warning saves are the ones that fire before impact: up to three answer at once, as Automatic Retaliation's do, and the rest stay for the victim's choice.

Every use is still a first use or an answer for the UN and the taboo. A salvo's taboo knock and UN record scale with the warheads landed, with diminishing returns; the figures are §14.

### 6.3 Decapitation

Only a target under Central Authorization, and only through warheads that land on its capital state (the Leadership mission, or any mission that strikes the capital).

- **Redundancy R** = 1 + stockpile ÷ 10, +2 with Satellite Communications, +1 with Mainframe Computers.
- **Chance** = max(0, (L − R) ÷ (L + R)), for L warheads landed on the capital. A 30-warhead power with Satellite Communications has R = 6, so it takes 7 or more on the capital to have any chance (owner call 7). A 3-warhead state has R = 1.3 and faces 21% from two.
- **Effect:** the answer is delayed, not lost. The victim cannot order its warheads for two to four weeks, after which "Command Restored" reuses the path of `nuclear_weapon_events.24`. A follow-up counterforce strike can land in that window.

Delegation, Launch on Warning and Automatic Retaliation are immune: that is part of their payoff.

### 6.4 The answer

`nuclear_weapon_events.1` sizes its answer from what survived. Automatic Retaliation's three are counted after counterforce losses, since it answers detonations; Launch on Warning's fly before them.

## 7. Range

### 7.1 Feasibility

The engine has no distance trigger, but it has topology:

- `has_strategic_adjacency` (direct, coastal, military-access or war-goal adjacency), which vanilla's alliance, defensive pact and rivalry AI use as `has_strategic_adjacency = scope:other_country`;
- `is_adjacent_to_country` and `is_land_adjacent_to_state`;
- `any_country_strategic_region`, already in the mod's `extra_effects.txt`;
- `any_neighbouring_state` at strategic-region scope;
- `is_coastal`.

That is enough for a coarse reach. Range matters for about one era: the bomb is era 6, ICBMs and missile submarines era 7. That is when it decides whom a first nuclear power can threaten.

### 7.2 Reach by delivery

| Delivery | Reaches |
|---|---|
| Bombers (Nuclear Weapons) | a country we have strategic adjacency to, or one with a state in a strategic region where we own a state; the same from a country that hosts our weapons (§7.3) |
| + Advanced Submarine Technology | also every country's coastal states |
| + ICBMs | everyone |

### 7.3 Basing

A new directed treaty article, **Nuclear Basing**: our weapons are stationed in the host. It extends our reach as if we owned the host's states, and it counts as a ready guarantee for the host (the protector term at full weight). This is what a deployment dispute objects to (§8.5), and what makes a bomber-era power's reach political: the stand-in for bombers in Britain or missiles in Cuba and Turkey.

### 7.4 Warning time

Even with global reach, weapons based in a country next to us cut our warning time: −10 to our effective survivability against that country, in §3.2, for that pair. That keeps deployment disputes meaningful after ICBMs.

### 7.5 Implementation and fallback

- **Reach is cached.** A monthly list per armed country (`nd_reach`, a variable list of countries), for armed countries only, so the iteration runs a few times a month, not per frame.
- **Its readers:** strike targets, the crisis's follow-through (a threat from a country that cannot reach us is a bluff: a new `nd_ft_reason` 8, −25), and the AI.
- **Fallback:** if reach proves impractical, deployment disputes read neighbors, a country that borders us (owner call 13).

## 8. Crisis subjects

### 8.1 War: the Suez model (owner call 9)

`nd_crisis_concede_war` drops the war goals the target's side holds against the issuer, or against its protégé, with `remove_war_goal = { who = <side> type = <type> }` for each type held (the UN Force's pattern, `common/scripted_effects/un_force_effects.txt:157`). War support falls by 15, down from 35. If the target holds no goals against us, so that we are the aggressor, only the war support falls. `remove_war_goal` addresses a side and a type, so a goal of the same type against another country in the same war goes too, as the UN code notes. Removing from a war and removing an opening goal are probed in §12.

### 8.2 Play: what is at stake

A new pressure part, `nd_yp_stakes`: the issuer's side's primary demands on the target, weighted by type. Annexation or reunification −30; a subjugation type (protectorate, dominion, tributary, personal union, crown land, chartered company) −20; a state transfer −10 each; a treaty, market, strait or minor goal −4 each. Capped at −40 and counting every primary demand (owner call 10). Unreasonable demands are refused, and a refusal moves the crisis toward Acute. The AI doesn't threaten where the stakes would hold pressure below its own concession line.

### 8.3 Co-belligerent cover (owner call 11)

`nd_has_armed_guarantor_against`, `nd_is_guaranteed_by` and `nd_dispute_guarantee_against` gain a third branch beside the treaty and the umbrella: a country believed armed, fighting on the same side as the beneficiary in a war against `$AGAINST$`, for that war only. It gets the protector term, "A Promise Called In" (once: the existing rule that skips a guarantor a treaty already reaches), the retaliation licence, and no nuclear shadow on the protégé's war support. Nothing was promised, so abandoning costs only −5 credibility: no `nd_guarantee_abandoned` and no word to other protégés. Plays don't count until they become wars.

### 8.4 Proliferation

`nd_dispute_proliferation_by` adds `$TARGET$ = { nd_believed_armed = no }`. Public belief, so an untested secret arsenal still counts. An armed rival's buildup is arms control's business: the `nuclear_arms_limitation` article.

### 8.5 New disputes

| Code | Dispute | Concession | Notes |
|---|---|---|---|
| 6 | A peacetime nuclear exchange between us in the last 24 months, or one that struck a country we cover | reparations (the `nuclear_loose.6` formula) and inspection of its custody (secured custody, as `nuclear_loose.6` grants) | Gives "Honor" after a peacetime strike something to open |
| 7 | Deployment: the target holds a Nuclear Basing article (§7.3), a guarantee or an umbrella over a country next to us, or has a Missile Defense Battery in a state next to us | end the article, or remove the battery's production method | Reach (§7) or neighbors (§7.5) |
| 8 | Claims: the target claims one of our incorporated states | `remove_claim` | Defensive only |
| 9 | Covert operations: the target runs an operation against us that we have detected | `remove_diplomatic_pact` on each | Covert operations are pacts |
| 10 | Orbital weapons: the target is building an Orbital Battlestation (`building_orbital_battlestation_construction_site`) | remove the construction site and a ten-year freeze | Needs a design pass with the Space Race system |

Classification order: 2, 1, 3, 6, 4, 7, 8, 9, 10, 5.

### 8.6 Trades

At the deadline, or under Our Moves, either side can offer a matching concession: a freeze for a freeze, basing for basing (Cuba for the Jupiters), a stand-down for a stand-down, a claim for a claim. Accepting closes the crisis as a new outcome, 11, "Trade": +5 credibility each and no climb-down. The AI accepts at pressure 40 or more when what it gives is no larger than what it gets, on the same weights as §8.2.

### 8.7 One crisis per country stays

"Honor" backs any number of threatened protégés without opening a crisis of its own (`nd_guarantee_act_honour`, `nuclear_crisis_effects.txt:2187`, sets `nd_crisis_backed` on the issuer's record). The limit only stops a second threat of a country's own.

## 9. AI summary

- Posture: §4.4.
- Launch under attack: §5.3.
- Claims and belief: §5.4.
- The planner: the AI orders Cities as it strikes now. It orders Forces when survivors(enemy against us) is under 3 after a counterforce strike of the size it can spare, and Leadership only under Warfighting against a Central target. Its weights are §14.
- Crisis opening: stakes (§8.2), reach (§7) and the new disputes (§8.5). The AI opens codes 6–9 defensively; code 10 only as a great power.

## 10. UI and the player guide

**Panel:**
- Forces: "Survivors against <rival>: N of M" for the main rival, with the breakdown on hover.
- Each authority's hover: its credit and decapitation line.
- The Strike section (§6.1).
- A Reach row while reach is limited.
- The crisis's pressure breakdown gains the stakes and issuer-exposure parts.

**Chapter 14 sections to update:** Survivability, reliability and crew strain; Launch authority; Opening a nuclear crisis; Crisis stages, danger and pressure; Moves during a crisis; Nuclear strikes (all three); Nuclear incidents and accidents; A nuclear exchange before war.

## 11. Tooling and tests

- `nuclear_incident_rates.py`: Acute-crisis and war cases, §2.3's table as its output, and the launch-under-attack decision. It keeps reading the script's own values; no tuning is copied into it.
- `nuclear_observer_report.py`: §2.4's counts, plus claims made, believed and exposed, counterforce destroyed, and decapitations.
- `TE_NUCLEAR:` records for claims, counterforce and decapitation, written at the call site with no `$PARAM$` inside the string (`test_nuclear_incident_risk.TestObserverRecords`).
- A Python mirror of the survivors formula, tested against the script values, as `nuclear_taboo_sim.py` mirrors the taboo.
- `test_nuclear_deterrence.py`: the new pressure and danger parts in the store effect, and the classification order.

## 12. Engine probes, in game while building

Probed 2026-10-28 (one observer game; details in `docs/guides/scripting_best_practices.md` § "War Goals, Plays, Adjacency and Claims"). Rows 9 and 10 are for phase 3.

| Question | Used by | Fallback | Result (2026-10-28) |
|---|---|---|---|
| `remove_war_goal` on a play that is a war | §8.1 | war support only (−35, as now) | Removes the **opening** goal; the war goes on. Did not remove goals added by script `add_war_goal`. AI-added goals untested: probe in phase 2 |
| `remove_war_goal` on a play's opening goal (the owner expects both to work) | §8.1 | skip the opening goal | Works, in a play and in a war |
| Does `who = <side>` take one country's goals or the whole side's? | §8.1 | accept the extra removals and say so in the tooltip | Untested: no added goal could be removed. Phase 2 |
| Does `resolve_play_for` enforce every goal or only primary demands? | §8.2 | stakes counts whichever it enforces | Every goal. Stakes count every goal (as built) |
| What `has_strategic_adjacency`'s coastal adjacency covers | §7.2 | `is_adjacent_to_country` plus the region test | Land and sea-coast neighbors; not distant coasts. `is_adjacent_to_country` covers sea-coast neighbors too |
| `any_neighbouring_state` at strategic-region scope | §7.2 | own regions only | Works |
| `remove_claim` on another country's claim, from script | §8.5 | drop code 8 | Works, history claims too |
| `remove_diplomatic_pact` on a covert operation's pact | §8.5 | end it through its maintain condition | Works |
| A list of states in the panel, for picking cities | §6.1 | keep `nuke_diplo_action` for one chosen city | Not probed (phase 3) |
| A salvo's option tooltip walks its effects without running away | §6 | fence it as `nd_launch_or_intercept` is fenced | Not probed (phase 3) |

## 13. Phases

Each phase updates `nuclear_crisis_design.md` §0, chapter 14 and the play-test list.

1. **Values and triggers.**
   - §3 without the exchange: the survivors measure and its readers, the ceiling, the danger part.
   - §4: authority payoffs, safeguards, the chance of a halt, the AI's posture.
   - §5.1 and §5.3.
   - §8.2, §8.3 and §8.4.
   - The in-crisis and in-war model, calibrated against §2.3.
2. **Concessions and the dilemma.** §8.1; code 6 of §8.5 with the "Honor" fix; §5.4.
3. **The exchange.** §6, the planner with counterforce and decapitation; survivors read with §6's losses.
4. **Range and the rest.** §7, then codes 7–10 of §8.5 and §8.6.

## 14. Open questions

1. §5.3 reverses part of the 2026-09-26 ruling: the government may order a launch under attack outside a war, in an Acute crisis, under any doctrine but No First Use. **Confirmed by the owner, 2026-10-28.**
2. Is launch authority public, as doctrine is? §5.4's belief and §3.3's three-quarters rule assume it is. **Public (owner, 2026-10-28).**
3. A salvo's taboo knock and UN record: how much each further warhead adds.
4. The AI's weights for Forces and Leadership missions, and how often it lies in a claim.
5. K's values against the arsenal sizes the AI builds.
6. Whether a Nuclear Basing host takes on custody risk and incident exposure for the weapons stationed with it.
