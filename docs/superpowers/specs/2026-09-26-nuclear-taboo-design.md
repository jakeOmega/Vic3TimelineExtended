# The nuclear taboo — design

## Context

`docs/systems/nuclear_crisis_design.md` §9 asked for it and nothing built it: "Reputation and nuclear taboo emerge from
use, pledges, opposition, and institutions, with configurable decay." Today every nuclear cost is a fixed number — a
strategic first strike is +25 infamy in 1950 and in 2050, in a world that has seen ten uses and in one that has seen
none — and holding an arsenal is pure upside (`nuclear_power`: +30 % prestige, +25 % leverage) whatever the world
thinks of the bomb. There is also no voluntary way out: an arsenal is given up only when someone else imposes a
`nuclear_disarmament` article, in a civil war, or on the Budapest path.

This document designs a world **nuclear taboo**: one score for how unthinkable nuclear weapons are, which moves toward
an equilibrium set by the state of the world, is knocked down by use and eroded by threats, and scales what every
nuclear act costs — up to making possession itself a burden. Agreed with the owner section by section on 2026-09-26.

Baseline: `main` at `b56f818d`. Branch `nuclear-taboo`.

The nuclear system's standing rule holds throughout: **everything here works with the UN, covert-warfare and
world-war systems disabled.** The UN is one driver among several, never a prerequisite.

## Owner rulings this rests on

| Ruling |
|---|
| One global score, 0–100. At the top, even holding the bomb is frowned on, threats are very costly and use makes a pariah; at the bottom the bomb is an ordinary weapon and costs nothing. |
| Threats and use lower it. It moves slowly on its own toward an equilibrium that depends on the world. |
| Left alone, it **strengthens up to a point** (the tradition of non-use). Drift alone must not reach the top: that takes international cooperation, through the UN or similar mechanics. |
| It is **born with the world's first warhead, low** (~20: "just a bigger bomb"). |
| It **feeds the AI**: "if you've created a world in which using nukes is normal, you should not be surprised when the AI uses them against you." |
| Possession costs: the bomb's prestige flips with the taboo; restraint-minded interest groups object; both scale with arsenal size, so a minimal deterrent is tolerated far more than a vast one. |
| There must be a way to get rid of the bomb, **and the AI must be capable of it**: unilateral full disarmament, unilateral reduction, and a bilateral arms-control treaty. |
| Threat effectiveness: a small effect in both directions (below, §4.3). |
| Cooperation that lifts the equilibrium: non-UN norms, the existing UN conventions, the Assembly's verdict on a use; a new Prohibition convention later (phase 3). |
| Infamy for use is **zero at taboo 0**: strategic = taboo, tactical = 0.4 × taboo (today's values at 25). |
| The Nuclear Weapons entry is **active for every country** once the taboo exists. |
| Band crossings fire **events** to every country, like global warming's thresholds. |
| Leaving an arms-control treaty costs only if it loosens the country's treaty obligations (§7.1). |
| A terror detonation from a loose warhead does not lower the taboo; it raises it a little. |

## 1. Architecture: the UN authority model

The score copies the equilibrium model `un_authority_values.txt` already uses (UN redesign phase 1), because it is
proven in this mod, explains itself in a breakdown, and keeps acts and the state of the world apart:

- A **target** is the sum of named **parts**, each computed from the state of the world and **snapshotted into a
  global** every month; the display reads the snapshots, never the sweeps (the entry re-renders every frame).
- The **score** closes a fraction of the gap to the target each month, with a maximum step.
- **Acts** (threats, doctrines, disarmament) write to a **decaying ledger**, one of the parts.
- **Use** also hits the score at once, as a **shock**.

Two alternatives were considered and rejected: a plain score with deltas and a drift toward a base (cannot express an
equilibrium that depends on the world, the core of the idea); and a per-country perceived taboo varying by ideology or
Rules of War law (every cost would depend on the observer; could be layered on later as per-country offsets from the
global number).

## 2. State, birth and the monthly step

| Global | Meaning |
|---|---|
| `nd_taboo` | the score, 0–100 |
| `nd_taboo_target` | the equilibrium, snapshotted monthly |
| `nd_tb_base`, `nd_tb_tradition`, `nd_tb_postures`, `nd_tb_restraint`, `nd_tb_un` (phase 2), `nd_tb_ledger` | the parts, snapshotted monthly |
| `nd_taboo_ledger` | the decaying ledger's running value |
| `nd_taboo_quiet_years` | the tradition clock: years of non-use, fractional |
| `nd_taboo_band` | the band last announced (§6.3) |
| `nd_taboo_last_use_year` | the year of the last use, for the panel |

**Birth.** At the first-warhead site in `nuclear_weapon_effects.txt` (the branch that sets `world_first_nuclear_weapon`
and fires `nuclear_weapon_events.9`), `nd_taboo_birth` sets `nd_taboo` to 20, the clock to 0, the ledger to 0, and the
target and parts at once. **Existing saves** in which warheads already exist: the monthly update seeds the same state
once when `world_first_nuclear_weapon` is set and `nd_taboo` is not.

Nothing reads the taboo before it is born: no one can use, threaten with or hold a warhead. Every reader nevertheless
goes through `nd_taboo_value`, which returns the birth value, 20, when the global is absent, so no script ever reads a
missing global.

**The monthly step.** `nd_taboo_monthly_update`, from a global-scope `on_monthly_pulse` in a new
`common/on_actions/nuclear_taboo_on_actions.txt` — never from the UN's pulse, which runs only once the UN is founded.
Gated on `nuclear_weapons_enabled` and on the taboo existing. In order:

1. Advance the clock: `nd_taboo_quiet_years` += 1/12.
2. Fade the ledger: × 0.9857 (a four-year half-life, the UN ledgers' factor).
3. Compute and snapshot every part; snapshot the target.
4. Step: `nd_taboo` += (target − score) / 36, clamped to ±1 a month (half a gap closes in about two years), then to
   0–100.
5. The band check and its events (§6.3).
6. The per-country sweep: possession cost, breakout detection, treaty-ceiling walk-outs (§5, §7.1).
7. One `TE_TABOO:` debug-log line: score, target, every part, the ledger, the clock.

## 3. The target

| Part | Range | Rule | Phase |
|---|---|---|---|
| **Base** | 20 | constant | 1 |
| **Tradition** | 0 … +35 | the quiet years, capped at 35: +1 a year without use, full after 35 years (1945 → 1980) | 1 |
| **Postures** | −10 … +10 | 10 × the rank-weighted **average** stance of the armed countries (below) | 1 |
| **Restraint** | 0 … +15 | +1 per non-use pledge pair in force (cap +5); +3 × rank weight per former nuclear state still disarmed (cap +10); phase 2: +2 × rank weight per country bound by an arms-control treaty (counted once) | 1 |
| **UN** | 0 … +15 | NPT (`un_agency_iaea`) and CPPNM (`un_agency_cppnm`) in force, × UN authority / 100; the Assembly's verdicts go to the ledger (§7.3) | 2 |
| **Prohibition** | 0 … +10 | the Prohibition convention | 3 |
| **Ledger** | −30 … +10 | the decaying record of acts (§3.2) | 1 |

The target is clamped to 0–100. **Drift alone tops out at 55** (base + full tradition); the other 45 points are
reachable only through cooperation, as the owner asked.

### 3.1 Postures and weights

Each armed country's **stance**, clamped to −1 … +1:

| Doctrine | Stance | Readiness | Adds |
|---|---|---|---|
| 1 No First Use | +1 | Recessed | +¼ |
| 2 Existential deterrence | 0 | High Alert | −¼ |
| 3 Flexible first use | −⅓ | | |
| 4 Compellence | −⅔ | | |
| 5 Warfighting | −1 | | |

The part is 10 × Σ(weight × stance) / Σ(weight) over armed countries (0 with none). An average, so one micro-state's
No First Use cannot swamp the world.

**Rank weight** (`nd_taboo_rank_weight`, country scope): great power 1.0, major power 0.5, minor power 0.25, anything
else 0.1. Read from `country_rank` when the act happens, so it needs no UN (`un_actor_weight` reads a share only the
UN's monthly update caches, and is 0 in a world without a UN).

### 3.2 What moves it

| Act | Shock to the score | Ledger | Weighted by | Hook |
|---|---|---|---|---|
| Strategic first use | −15 | −10 | nothing | `nd_record_nuclear_use` |
| Tactical first use | −6 | −4 | nothing | `nd_record_nuclear_use` |
| Retaliation, either kind | half | half | nothing | `nd_record_nuclear_use` (`nd_was_struck_by`) |
| Tradition clock | a first use **halves** the quiet years; retaliation cuts them by a quarter | | | `nd_record_nuclear_use` |
| Public ultimatum | | −1 | rank | `nd_crisis_open`, public |
| Private warning | | −0.3 | rank | `nd_crisis_open`, private |
| Adopting Compellence or Warfighting | | −1 | rank | `nd_set_doctrine` with `OFFENSIVE = yes` |
| Repudiating No First Use, or breaking a pledge | | −1.5 | rank | `nd_break_pledge_effects` |
| Adopting No First Use | | +0.5 | rank | `nd_set_doctrine` with `D = 1`, **not** when `nd_weekly_update` binds the doctrine to the No-First-Strike amendment (the law's act, not the government's; the binding call site passes a flag) |
| A crisis ending in a reciprocal stand-down | | +0.5 | nothing | `nd_crisis_close`, outcome 3 |
| Giving up an arsenal, any path | | +1 + 0.1 per warhead, cap +6 | warheads | `nd_taboo_note_renunciation` (§5.1) |
| Retiring a warhead under a ceiling | | +0.05 each | warheads | the retirement step (§5.3) |
| A loose-warhead terror detonation | | **+2** | nothing | the detonation in `nuclear_loose_effects.txt`: no state chose it, and the world tightens up after a horror no one can answer |
| A former nuclear state re-arming (breakout) | | −2 | rank | the monthly sweep (§5.1) |
| Walking out of arms control | | −1 | rank | the monthly sweep (§7.1) |

Use is unweighted — a detonation is a detonation, as the UN ledger already treats it
(`un_ledger_actor_entry_unweighted_on`). Threats and doctrines are weighted by rank: the UN redesign's lesson (its §1.1)
is that flat per-actor deltas let a micro-state move the world as much as a superpower. Disarmament is weighted by
warheads given up.

How it plays: a first strategic use in a young world (~20) drops it to about 5, with the target around 10–15, and it
recovers over decades. A mature world at 60 goes to 45 and its target falls by about 27 (−10 from the ledger, −17 as
the tradition halves): **one use roughly halves a mature taboo** over the following years — the "taboo is broken"
moment `nuclear_weapon_events.16`'s flavour already describes.

Every writer goes through `nd_taboo_ledger_add = { POINTS = … }` and `nd_taboo_shock = { POINTS = … }`, which clamp
and keep the ledger inside −30 … +10. Any event option that moves the score or the ledger says so in a
`custom_tooltip` (`silent_variable_audit`).

## 4. What it does

Today's fixed numbers become, roughly, the value at a young taboo. All readers go through `nd_taboo_value`.

### 4.1 Use

| | Today | Scaled | At 0 / 20 / 50 / 100 |
|---|---|---|---|
| Strategic first use, infamy (`extra_effects.txt`, `nuclear_first_strike`) | 25 | taboo | 0 / 20 / 50 / **100** |
| Tactical first use, infamy (`nd_tactical_strike_resolve`) | 10 | 0.4 × taboo | 0 / 8 / 20 / 40 |
| **World reaction (new)**: relations with every country but the victim | none | −0.4 × taboo | 0 / −8 / −20 / −40 |
| The victim's relations | −50 | unchanged | |
| Retaliation's infamy | none | none: it is licensed, deterrence working | |

**"Pariah" is vanilla's pariah tier** (infamy ≥ 100): at a maximal taboo one strategic strike lands there, and infamy's
5-a-year decay keeps the striker Notorious for about a decade. No separate pariah modifier: infamy already drives the
AI's hostility and doubles pact costs. The world-reaction relations line sits in `nd_record_nuclear_use` behind one
`custom_tooltip` (an `every_country` renders every member in a preview).

### 4.2 Threats and doctrine

| | Today | Scaled |
|---|---|---|
| Public ultimatum, infamy (`nd_crisis_preview`) | 5 | 0.1 × taboo |
| Adopting an offensive doctrine, infamy (`nd_set_doctrine`) | 5 | 0.1 × taboo |
| The bilateral relations hits (−20 target, −10 rivals); a private warning | | unchanged |

The crisis preview and the doctrine buttons already print these lines, so the scaled number shows before committing.

### 4.3 Threat pressure

A twelfth part of the target's yield pressure, **`nd_yp_taboo`** = (50 − taboo) × 0.16: +8 at taboo 0, 0 at 50, −8 at
100. Its negative side is **halved for a public ultimatum**: in a high-taboo world a threat is doubted, but issuing one
publicly spends reputation, and that price is itself the signal (the owner's reasoning; the infamy in §4.2 already
charges it, so it is not counted twice). Stored on both parties like the other parts by `nd_crisis_refresh_figures`,
so the pressure breakdown shows it, and the target's AI reads it through `nd_yield_pressure` with no extra wiring.

### 4.4 Possession

Both costs read one number:

> **possession burden** (`nd_taboo_burden`, country scope) = taboo factor × arsenal factor, 0–1
> - taboo factor = 0 below 40, then (taboo − 40) / 60
> - arsenal factor = 0.2 + 0.8 × min(stockpile, 50) / 50 — 0.28 at 5 warheads, 0.6 at 25, 1.0 at 50 or more

The arsenal factor saturates at 50, the count the upkeep's custody term already stops at; AI arsenals top out at 25
(`nuclear_ai_desired_stockpile`), and a saturation at 100 would have kept every AI below 40 % of the burden.

1. **`nd_taboo_possession_cost`**, a static modifier on the entry (`je:je_nuclear_program`, the upkeep's scope), per
   unit country_prestige_mult −0.45 and country_leverage_generation_mult −0.25, applied with `multiplier =` the
   burden, removed and re-added each month as the burden moves (the dynamic-modifier scaling pattern). One refresh site, the monthly sweep, with a tracker variable (`nd_taboo_cost_on`) because add/remove results
   are invisible in the same block; it comes off when the burden is 0 **or the country is not armed** (the entry no
   longer closes on disarmament, §6.1). `nuclear_power` is left exactly as it is: it is tested as a boolean elsewhere
   (the NPT's enforcement gate, the nuclear-shadow war-support line), and scaling it would also flip its maneuvers.
   Net: a 50+ arsenal at taboo 100 goes from +30 % prestige to −15 % and its leverage bonus to zero; a 5-warhead
   minimal deterrent in the same world keeps +17 %.
2. **Domestic pressure**, `nd_ig_term_possession_value`, a sixth term in `nd_ig_stance_value`: restraint-class groups
   (`nd_ig_class_restraint`), burden ≥ ⅓ → −1, ≥ ⅔ → −2. Not tenure-gated — holding warheads is not a posture choice.
   Stored on the group with the other terms (`nd_ig_store_opinion`), so the At Home list prints it.

## 5. Unilateral exits

### 5.1 Renounced status, and breakout

**`nd_renounced_modifier`**, a country static modifier carrying the existing `country_nuclear_disarmament_bool`. Every
gate built for a treaty-disarmed country then applies: the programme cannot run (`nuclear_program_can_run_programme`),
`nd_is_armed` is false, and the NPT's enforcement treats the country as non-nuclear. It is mirrored in the variable
**`nd_renounced`** (the year) and rebuilt from it by the monthly sweep — a revolution's winner inherits variables but
not modifiers (`scripting_best_practices.md` § "What a Civil War's Winner Inherits"; the winner continues the nation).

**`nd_taboo_note_renunciation`** (country scope, called **before** the stockpile is zeroed) books +1 + 0.1 × warheads
(cap +6), sets `nd_renounced`, and fires a renunciation marker on the history chart. It is **idempotent**: a country
already holding `nd_renounced` with no warheads is not counted again — the Budapest path may put a disarmament article
in force (whose `on_entry_into_force` calls it) and then zero the stockpile itself. Callers:

- `nuclear_disarmament`'s `on_entry_into_force` (`extra_treaty_articles.txt`);
- `nd_bp_accept` (the Budapest path: guarantees only, or through the lead's disarmament article);
- `nd_cw_dismantle_as` (the civil-war dismantle and both "Deny Them the Bomb" dismantles);
- the new Dismantle the Arsenal, on completion.

Only the new dismantle applies `nd_renounced_modifier`; the other paths carry their own gates or none.

**Breakout.** The monthly sweep finds a country holding `nd_renounced` that is armed again, by any route — including
one whose disarmament treaty lapsed and which rebuilt — clears the variable and books −2 × rank weight.

### 5.2 Dismantle the Arsenal

A posture-panel action. Not at war, not in a nuclear crisis, not in a civil war (`nd_in_civil_war`).

- Takes 12 months, + 1 per 10 warheads above 20, at most 36 (`nd_dismantle_months_left`, `nd_dismantle_per_month`);
  warheads retire evenly across it. Readiness is locked at Recessed and the programme frozen throughout.
- Each month's retirement goes through the custody ledger (`nd_ledger_refresh`); nothing is added to the loose pool.
- **Halt the Dismantling** at any time: what is retired stays gone; −10 credibility and −1 × rank weight on the ledger
  (a public reversal).
- On completion: `nd_taboo_note_renunciation` counting the arsenal at the start (`nd_dismantle_start_stock`, stored when the dismantling begins), `nd_renounced_modifier`,
  **relations +0.2 × taboo with every country** (0 … +20), **`nd_renunciation_prestige`** — a 20-year decaying prestige
  bonus, `multiplier` = taboo / 100 on a +20 % unit — a one-off approval for restraint groups and disapproval for hawks
  (`nd_ig_is_restraint`, `nd_ig_is_hawk`). A renunciation in a world that prizes it is worth more than in one that
  does not.

**Resume the Nuclear Programme**, a decision in `common/decisions/extra_decisions.txt` (the entry's buttons cannot carry
it: a renounced country's posture panel is not drawn). Visible with `nd_renounced_modifier`. Removes it and the
renunciation prestige; infamy 0.1 × taboo; relations −0.2 × taboo with every country. The breakout entry follows once
the country is armed again.

### 5.3 Reduce the Arsenal

A posture-panel stepper, **Arsenal ceiling: N** (`nd_warhead_ceiling`; unlimited when absent; minimum 1 — zero is the
dismantle). Warheads above it retire at max(1, 10 % of the excess) a month through the custody ledger, +0.05 on the
ledger apiece. The programme builds nothing while at or above the ceiling (`nuclear_program_weekly_progress`). Raising
the ceiling is free: the ledger credit decays on its own, and rebuilding costs the programme's money. The panel shows,
beside the stepper, the arsenal size at which the burden would drop a domestic step.

### 5.4 The AI

In `nd_ai_review_posture` (every sixth month), not through journal-entry buttons (a weighted roll over posture buttons
would make it a lottery; `nuclear_crisis_design.md` §0.2):

- **Reduce** when the stock is above 1.5 × `nuclear_ai_desired_stockpile` (taboo-scaled, §8.4) and the burden
  is above 0: set the ceiling to the desired stockpile. Lift it when the desired number rises past it (a war).
- **Dismantle** when all hold, then with 20 % a review (so the world does not disarm in one month): burden ≥ 0.3 or
  taboo ≥ 70; `nd_has_plausible_attacker = no`, not at war, not in a crisis; covered by a guarantee or umbrella
  (`nd_is_guaranteed`) **or** not a great power; `nd_regime_is_militarist = no`; `ruler_is_aggressive = no`.
- **Halt** only at war with an armed enemy that threatens its existence (`nd_enemy_threatens_existence`).
- **Resume** (the decision's `ai_chance`) when an armed country threatens it (a war, or an antagonistic armed rival)
  and the taboo is below 50.
- **The existing `nuclear_disarmament` article:** its AI evaluation gains a taboo term, so demands succeed more often
  in a high-taboo world.

## 6. Display

### 6.1 The entry is active for every country

`nuclear_program_entry_applies` gains a branch: the taboo exists, `nuclear_weapons_enabled`, and not decentralized.
Before the first warhead the old gate holds. Consequences the plan must carry out and check:

- **Disarmament no longer deactivates the entry.** The posture modifiers and the possession cost came off *because the
  entry closed*; they must now come off *because the country is not armed*, and both refresh sites key off
  `nd_is_armed`. `mod_systems.md`'s "Disarmament deactivates the entry" paragraph and `journal_entry_systems.md` are
  rewritten.
- **Every pulse effect must be a cheap no-op for an unarmed country** — already the entry's rule, now exercised
  weekly by ~200 countries rather than ~10. The plan audits each pulse effect's early exit.
- The programme, posture and crisis panels keep their gates; a non-nuclear country sees the taboo panel, the nuclear
  powers and (when relevant) a crisis.

### 6.2 The taboo panel

A new area at the top of `widget_je_nuclear_balance`:

- **Score and band** ("Nuclear taboo: **47** — Fragile") and where it is heading ("rising toward 58").
- **Target breakdown** tooltip — base, tradition (with the quiet years), postures, restraint, UN, ledger — printed from
  the snapshots by a script-built display handler (`nd_taboo_breakdown_sgui`, the crisis breakdowns' pattern), adding
  up to the target.
- **What it costs now**: strategic and tactical first-use infamy, public-ultimatum infamy, and while armed the
  **possession burden** with its prestige and domestic effect.
- **A history chart** of score and target (`te_history_chart`, as the UN authority and global-warming charts), collapsed
  by default, with markers for each use and each renunciation.

The `nd_disp_taboo_*` values read snapshots only.

### 6.3 Band events

| Band | Range | Ties |
|---|---|---|
| Normalised | 0–29 | the AI loosens below 30 |
| Fragile | 30–49 | the possession burden starts at 40 |
| Established | 50–69 | |
| Strong | 70–89 | the AI uses first only for survival from 70 |
| Absolute | 90–100 | |

Crossing a boundary fires an event to every non-decentralized country, on the global-warming pattern
(`gw_fire_warming_threshold_event`): **four boundaries × two directions**, `nuclear_taboo.1`–`.8`. Hysteresis ±2 (a
boundary is crossed upward at +2 above it, downward at −2 below). Each boundary-and-direction fires **at most once in
ten years** (the year it last fired, per event: `nd_taboo_ev_<n>_year`, compared rather than a timed variable), because
the taboo, unlike temperature, can oscillate.

Options are **country-local and never move the global score** — 200 countries each nudging one number is the UN
redesign's lesson. Where it fits, an option enacts the real system action (banking #428's pattern of events deferring
to the dashboard), with armed and unarmed option sets:

- **Hardening, armed:** *Cut the arsenal* (sets the ceiling to half the stock, min 1); *Begin dismantling* (where its
  gate holds); *Adopt No First Use* (where tenure allows); against *Our deterrent is not negotiable* (hawks pleased).
- **Hardening, unarmed:** *Champion the norm* (prestige, relations with other unarmed countries) or *Stay quiet*.
- **Eroding, unarmed:** *Seek a protector's guarantee* (relations with the strongest friendly armed power); *Fund a
  programme* (one funding step, where eligible); *Build shelters and civil defence* — `nd_civil_defence_modifier`, ten
  years, costing 5 upkeep units (the posture upkeep's 1/100,000-of-GDP-a-week unit) and **halving the nuclear-shadow
  war-support drain** (`WAR_SUPPORT_TE_NUCLEAR_SHADOW` in `zz_te_war_support_injections.txt`, −0.25 → −0.125) while it
  holds.
- **Eroding, armed:** *Modernise the arsenal* (programme progress) or *Hold the line* (restraint groups pleased).

The texts are written in the plan; each event follows `event_creation_guide.md` (image, option tradeoffs, AI weights
that read the same triggers the options enact).

### 6.4 Tooling

- The monthly `TE_TABOO:` debug-log line (§2).
- `te_debug_nuclear` gains options: set the score, age the clock ten years, fire a renunciation, and print the parts.

## 7. Phase 2

### 7.1 The arms-control article

`nuclear_arms_limitation`, a mutual article. While in force each party's **treaty ceiling** holds the programme as
the unilateral ceiling does (§5.3), and warheads above it retire the same way.

- **The ceiling.** First step of phase 2: check whether an article can take a numeric input (vanilla's money and goods
  transfers take a `quantity`). If yes, the parties negotiate it. If not, a SALT-style rule: each party's stock on
  ratification, cut by 25 %.
- **No breach is possible**: the programme cannot build above the ceiling.
- **Walking out** costs only when it loosens the country's treaty obligations. The monthly sweep stores each
  country's lowest treaty ceiling (`nd_treaty_ceiling`) and the partner that holds it (`nd_treaty_ceiling_partner`).
  When the lowest treaty ceiling **rises or vanishes** — a treaty lapsed, broken, withdrawn from, or renegotiated
  upward — it books −1 × rank weight. Not booked when the stored partner no longer exists (a lapse nobody chose).
  - A treaty superseded by a stricter one can be dropped free (the lowest treaty ceiling does not move), so the
    maintenance incentive points the right way.
  - **The unilateral ceiling never shields an exit.** Setting a binding unilateral ceiling, leaving every treaty and
    then loosening it pays at the second step: only another *treaty* holds the lowest treaty ceiling in place.
- **Taboo:** each country bound by at least one such treaty counts once, rank-weighted, in the restraint part (so
  stacking redundant treaties earns nothing).
- **AI:** evaluation reads the taboo, the burden, and parity with the other party. The usual traps are checked:
  same-draft conflicts only in `can_ratify`; leverage placement (`treaty_leverage_side_audit`).

### 7.2 The UN's conventions

The UN part (0 … +15): NPT in force + (UN authority / 100) × 8; CPPNM in force + (UN authority / 100) × 4. Zero without
a UN.

### 7.3 The Assembly's verdict on use

The docket's nuclear grievance (`un_docket_note_grievance KIND = nuclear`) leads to a condemnation. When its vote
resolves (`un_vote.2`, the condemn topic on a nuclear grievance — the hook to verify first): **passed**, ledger +3 and a
+2 shock ("the world said no"); **failed or vetoed**, ledger −3 ("impunity").

## 8. The AI (phase 1)

### 8.1 Use

`nd_ai_nuclear_use_justified`:
- **Taboo ≥ 70:** first use only for national survival (`nd_enemy_threatens_existence`), whatever the doctrine.
  Retaliation unaffected.
- **Taboo < 30:** the "a cautious ruler only for survival" brake lifts.
- Deterrence logic (can they answer, the reserve, the six-month pause) is unchanged at every taboo: the taboo governs
  restraint, not calculation.

Both strike actions' `evaluation_chance` (`nuke.txt`) × `nd_taboo_ai_use_factor`: ×2 at taboo 0, ×1 at 35, ×0.3 at
100 (linear between).

### 8.2 Threats

`nd_ai_would_issue_ultimatum`: at taboo ≥ 70 no *coercive* public ultimatum; defensive ones (a guaranteed country, its
own survival or core) still go out. Private warnings unaffected.

### 8.3 Doctrine

In `nd_ai_review_posture`'s random list: No First Use + (taboo − 50) × 0.3 above 50 (up to +15); Compellence and
Warfighting +10 below taboo 30, ×0.25 at 70 or more; Flexible −5 at 70 or more. Low-taboo worlds drift toward
permissive doctrines, which the actions' doctrine gates then honour.

### 8.4 Arsenal size and proliferation

`nuclear_ai_desired_stockpile` (`extra_script_values.txt`) × a taboo factor: ×1.3 at taboo 0, ×1 at 40, ×0.5 at 100,
never below 1 — the funding buttons, the events that read it and the reduction target (§5.4) all follow. At taboo ≥ 70,
`increase_funding_nuclear_program`'s `ai_chance` × 0.25 for a country with no plausible attacker and no war.

## 9. Files

| New | |
|---|---|
| `common/scripted_effects/nuclear_taboo_effects.txt` | birth, monthly update, ledger/shock writers, renunciation, dismantle, reduction, band events' dispatch |
| `common/scripted_triggers/nuclear_taboo_triggers.txt` | bands, dismantle/resume gates, AI judgements |
| `common/script_values/nuclear_taboo_values.txt` | every constant at the top; parts, weights, burden, scaled costs, display |
| `common/static_modifiers/nuclear_taboo_modifiers.txt` | `nd_taboo_possession_cost`, `nd_renounced_modifier`, `nd_renunciation_prestige` |
| `common/on_actions/nuclear_taboo_on_actions.txt` | the global monthly pulse |
| `events/nuclear_taboo_events.txt` | `nuclear_taboo.1`–`.8` |
| `test_nuclear_taboo.py` | §10 |
| `scripts/analysis/nuclear_taboo_sim.py` | §10 |

Edited: `nuclear_deterrence_effects.txt` (`nd_record_nuclear_use`, `nd_set_doctrine`, `nd_break_pledge_effects`,
`nd_ai_review_posture`, the refresh sites), `nuclear_crisis_effects.txt` (`nd_crisis_open`, `nd_crisis_preview`,
`nd_crisis_close`, `nd_crisis_refresh_figures`), `nuclear_deterrence_values.txt` (`nd_yp_taboo`,
`nd_ig_term_possession_value`), `nuclear_deterrence_triggers.txt` (AI), `extra_effects.txt` (strike infamy),
`nuclear_custody_effects.txt` (`nd_cw_dismantle_as`, `nd_bp_accept`), `nuclear_loose_effects.txt` (terror
detonation), `nuclear_weapon_effects.txt` (birth, the ceiling), `nuke_triggers.txt` (`nuclear_program_entry_applies`),
`extra_treaty_articles.txt` (renunciation, AI term), `extra_script_values.txt` (desired stockpile), `nuke.txt`
(evaluation chance), `zz_te_war_support_injections.txt` (civil defence), `nuclear_program_buttons.txt` (proliferation weight), `extra_decisions.txt` (Resume), the posture
and balance widgets with their sguis and custom loc, loc, docs (`nuclear_crisis_design.md` §0.11, `mod_systems.md`,
`journal_entry_systems.md`).

## 10. Testing and verification

- **`test_nuclear_taboo.py`** — static checks that fail naming the site: every renunciation path calls
  `nd_taboo_note_renunciation`; every use books through `nd_record_nuclear_use`; no literal infamy survives at the
  scaled sites (§4.1, §4.2); every part has its snapshot global and `nd_disp_*` value; all eight band events exist
  with loc; new panel ops agree across the sgui, the `.gui` and the docs (as `test_nuclear_deterrence.py`).
- **`scripts/analysis/nuclear_taboo_sim.py`** — a port of the monthly step reading every constant from the script
  files (as `nuclear_incident_rates.py`). Scenarios: a quiet century (must plateau at 55); one use in year 10, and one
  in year 40; a No First Use world with pledges and a renunciation; a normalised world with repeated use. Its table
  goes into §0.11, so the constants are justified by curves.
- Every `--strict` audit clean on reload; unit tests; ruff.
- **In-game checklist** as `nuclear_crisis_design.md` §0.11: the everyone-active entry's pulse cost, the panel and its
  breakdown, a band event, a dismantle start to finish, the AI reducing, the possession modifier's values in the
  prestige tooltip, the scaled infamy in the strike and ultimatum previews.

## 11. Phases

1. **Phase 1:** §2–§6 and §8 — the score, the costs, possession, the unilateral exits, the display, the AI, the non-UN
   norms.
2. **Phase 2:** §7 — arms control, the UN conventions, the Assembly's verdict.
3. **Phase 3:** the Prohibition convention, in its own spec (the convention registry is ~30 hand-kept sites across
   20 files).

The implementation plan covers phases 1 and 2.

## 12. Known roughnesses and open items

- `nuclear_power`'s leverage *resistance* (+25 %) is not offset; only generation is. Deliberate: a burden on
  influence, not on standing firm.
- `nd_civil_defence_modifier` is a modifier only, so a revolution's winner loses its shelters' effect (ten-year
  flavour; not mirrored).
- The taboo is global; a regional or ideological layer (§1, the rejected alternative) is left for later.
- The numeric-input question for the arms-control article (§7.1) decides its shape.
- The UN verdict hook (§7.3) is to be verified before it is built.
