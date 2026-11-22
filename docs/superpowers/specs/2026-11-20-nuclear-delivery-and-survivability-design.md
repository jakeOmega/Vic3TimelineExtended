# Nuclear Delivery Projects and Survivability — Design

> **Status (2026-11-20): no open questions. Phase 1 has a plan, [`plans/2026-11-20-nuclear-delivery-phase1.md`](../plans/2026-11-20-nuclear-delivery-phase1.md); both its halves, the model (PR 1a) and the display (PR 1b), are built (`nuclear_crisis_design.md` §0.18). Phase 2, the delivery projects, has its plan, [`plans/2026-11-20-nuclear-delivery-phase2.md`](../plans/2026-11-20-nuclear-delivery-phase2.md); both its halves, the projects (PR 2a) and what the panel tells of them (PR 2b), are built (`nuclear_crisis_design.md` §0.19, §0.20). §10's later work has no plan yet.** Baseline `main` at the branch point of this spec. The owner's calls from the 2026-11-20 discussion are §1 (calls 9 to 13 answer the draft's open questions); everything else is a proposal, and every number is a first tuning value. Phases are §9.
> Read first: [`docs/systems/mod_systems/nuclear.md`](../../systems/mod_systems/nuclear.md) and [`docs/systems/nuclear_crisis_design.md`](../../systems/nuclear_crisis_design.md) §0, what shipped; the [crisis rework spec](2026-10-28-nuclear-crisis-rework-design.md) §§3, 4 and 7, which this changes. When a phase ships, update §0 of `nuclear_crisis_design.md`, `mod_systems/nuclear.md`, chapter 14 of the player guide and `docs/testing/nuclear-playtest.md`.

The aim, in the owner's words: model the incentives behind nuclear decisions and strategy in the Cold War, and present the information to the player clearly.

## 0. Why

1. **A technology switches on deployed hardware, for every armed country, the day it is researched.** The `ICBMs` technology gives reach to every state (`nd_state_in_reach_of`, `nd_reaches_country`, `nd_reach_limited`, `common/scripted_triggers/nuclear_deterrence_triggers.txt:795–840`), +20 to the survivability ceiling for silos (`nd_survivability_cap`, `common/script_values/nuclear_deterrence_values.txt:184`), +0.5 to the counterforce ratio (`nd_k_ratio`, `:725`), Launch on Warning and Automatic Retaliation (`nd_can_adopt_launch_on_warning`, `nd_can_adopt_automatic_retaliation`, `nuclear_deterrence_triggers.txt:217–226`), silo accidents (`events/nuclear_incident_events.txt:1134`, `:1399`) and +0.5 nuclear attack success (`common/technology/technologies/era_7.txt:369`). A country whose programme runs on foreign aid gets global reach with its first warhead, and stealing the technology (`covert_tech_steal_military`) hands it over too. Range, which rework phase 4a made matter in peacetime crises, stops mattering for a country the day it finishes one era-7 technology.
2. **Advanced Submarine Technology does the same with less.** It needs only Sonar and Nuclear Energy: no missiles and no bomb. It gives an armed country reach to every coastal state in the world (`nuclear_deterrence_triggers.txt:813`, `:830`) and +25 to the survivability ceiling (`nuclear_deterrence_values.txt:188`), the largest single step. **Neither read asks for a coast, so a landlocked armed country gets both** (a bug, fixed in phase 1). Once ICBMs are gated, submarines would hand out most of their reach for free.
3. **Survivability's flat ceiling hides what technology does.** The parts add up (25 bombers, +15 Radar, +20 ICBMs, +25 submarines, +10 missile defense) and stop at 80 (`max = 80`). Radar, ICBMs and submarines alone make 85, so Missile Defense Systems then adds nothing, while the ceiling's tooltip (`nd_w_survivability_cap_tt`) and the player guide say each part raises it. At the ceiling, Launch on Warning saves 12 points of a full first strike however secure the force, and nothing built later can lower that.
4. **After the first device the programme has one output.** Funding buys warheads and nothing else, so there is no choice between how many warheads, how far they reach and how many survive.
5. **Several decisions are made without their payoff in view.** The launch authority choices list their modifier lines ("Launch Credit +60%") but not what that saves in warheads. The hardening stepper says survivability "climbs faster" without saying how fast or to where. The Strike section's Forces and Leadership missions describe their effects in words, with no expected result for the salvo the player has set up. Launch credit appears only inside the Survivors tooltip ("Share launched before impact").

## 1. Owner calls (2026-11-20)

| # | Call |
|---|---|
| 1 | Fielding ICBMs is a project on the Nuclear Weapons entry, run like the first device. The technology keeps what is knowledge. What is hardware moves to the project, including the technology's +0.5 nuclear attack success. Later attack and defense modifiers (a strategic defense programme, say) may follow the same pattern |
| 2 | Deferring a project is always open, not only in a crisis. A country whose enemies are all in bomber reach (India and Pakistan) has little reason to build range |
| 3 | Warheads taken into custody arrive without their delivery; the new holder delivers them by its own means |
| 4 | Missile submarines, the third leg, get a project too |
| 5 | No anti-submarine counter. The Anti-Submarine Warfare technology protects fleets in battle; it doesn't hunt missile submarines across the oceans, and even the US never got that far enough to plan a first strike on submarines at sea |
| 6 | Survivability has diminishing returns and no flat ceiling |
| 7 | Against an enemy with Precision-Guided Munitions, silos protect less: the 1970s window of vulnerability |
| 8 | Every value a decision rests on is shown to the player, except those hidden on purpose. An audit agent reviews the visibility section (§5.5) |
| 9 | The Nuclear Disarmament article and a completed dismantling remove the fielded legs (§4.4) |
| 10 | With Precision-Guided Munitions, both effects stay: the counterforce ratio's +0.5 and the silo penalty. Each must be communicated clearly (§3.4) |
| 11 | The submarine leg's upkeep starts at the proposed figure and is tuned in play-testing (§4.3) |
| 12 | The AI builds warheads first until it holds half the arsenal it wants. Better still, it scores how useful short range is against long range: if nobody who matters is in short range, it gets the range first (§4.5) |
| 13 | The two reads that go past the world's view move to it in phase 1: a side's crisis pressure and the opening preview counting the other side's true survivors, and the believed command redundancy (§5.2) |
| 14 | A figure about another country that rests on the world's view says so: a short qualifier on the figure itself ("up to", "at least", a range), and a hover that explains the assumption in full (§5.2) |

## 2. The incentives this models

The design is judged by whether these Cold War pressures appear in play, for the player and the AI alike.

- **Quantity, range or survival.** After the first device a programme chooses what to build next. A country whose enemies are its neighbors builds warheads (India and Pakistan). One with a distant rival builds ICBMs (the United States and the Soviet Union). One whose small arsenal could be destroyed on the ground goes to sea (Britain and France).
- **A secure second strike calms the trigger finger.** The more of a force survives a first strike, the less Launch on Warning saves, so its accident risk is worth less. A vulnerable force has every reason to launch early (§3.3).
- **Accuracy erodes silos.** A rival's precision weapons make silo forces easier to destroy, which pushes a silo power to sea or back toward Launch on Warning (§3.4).
- **Arms control binds warheads, not delivery.** Ceilings cap warheads; a freeze stops the whole programme (§4.1).
- **Delivery is public.** The world sees missile tests and submarine launches, so fielded legs are public, as doctrine and launch authority already are (rework spec §14.2). True arsenals stay hidden (§5.2).

## 3. Survivability as a product

### 3.1 The target

The ceiling (`nd_survivability_cap`, `max = 80`) is replaced by a **target**: each part removes a share of whatever is still exposed to a first strike.

Exposed share = 0.75 (bombers, always) × 0.80 (Radar) × 0.70 (ICBMs fielded) × 0.50 (missile submarines fielded) × 0.85 (Missile Defense Systems), with a factor of 1 for each part not held. Target = 100 × (1 − exposed share).

| Forces | Today | Target |
|---|---|---|
| Bombers | 25 | 25 |
| + Radar | 40 | 40 |
| + ICBMs | 60 | 58 |
| + missile submarines | 80 (85, capped) | 79 |
| + Missile Defense Systems | 80 (95, capped) | 82 |
| Bombers, Radar, ICBMs, missile defense (no submarines) | 70 | 64 |

Every part always counts, by less the more is already protected, and nothing reaches 100. Submarines' factor of 0.5 is the largest single cut, which makes them the hardest leg to destroy without a rule of their own. That factor is the dial if they should count for more.

- **Script.** `nd_survivability_target` (new, `nuclear_deterrence_values.txt`) replaces `nd_survivability_cap` at every reader: the step (`nd_survivability_step`), the floor (`nd_survivability_floor`, still 30% of it), `nd_exposed_warheads_ceiling_r2` and its `_vs_saved` copy (renamed `_target_`), the posture effect at `nuclear_deterrence_effects.txt:94` and `nd_display_survivability_cap` (renamed `nd_display_survivability_target`). Each factor is its own script value (`nd_exposure_factor_bombers`, `_radar`, `_icbms`, `_submarines`, `_missile_defense`) so the panel can print the chain (§5.4) and the analysis script can mirror it.
- **Unchanged:** hardening's climb (2% of the gap per level per month) and the decay without it, the readiness factors (×0.5 Recessed, ×0.8 Routine, ×0.9 Heightened, ×1 High Alert), launch credit, the counterforce ratio, the survivors formula and command redundancy's survivability ÷ 20 (at most +4.1 now).
- **Saves.** A country above its new target settles toward it through the existing step, which already handles a figure above the ceiling (the 95 → 80 change). No migration.

### 3.2 Call 5 still holds

Rework owner call 5, "the highest survivability may need both hardening and a fast authority", still holds: the lowest losses still need hardening plus Launch on Warning (§3.3). What changes is that the gap a fast authority closes now shrinks as forces improve, rather than being held at 12 points by the cap. Rework §3.1's comment ("The last stretch toward full security has to come from a fast launch authority … not from technology") is replaced by this section.

### 3.3 What a full first strike destroys

Lost = min(what the rival's arsenal could destroy, exposed warheads) × (1 − launch credit), as today (`nd_survivors_vs_*`). Against a rival large enough to reach every exposed warhead, at High Alert, with no safeguards:

| Forces (target) | Central | Delegation (0.25) | Launch on Warning (0.6) | What Launch on Warning saves |
|---|---|---|---|---|
| Bombers and Radar (40) | 60% | 45% | 24% | 36 points |
| + ICBMs (58) | 42% | 31.5% | 16.8% | 25 points |
| + missile submarines (79) | 21% | 15.8% | 8.4% | 12.6 points |
| + Missile Defense Systems (82) | 17.9% | 13.4% | 7.1% | 10.7 points |
| Today, at the ceiling of 80 | 20% | 15% | 8% | 12 points, whatever else is held |

### 3.4 Silos against accuracy (owner call 7)

Against an enemy with `precision_guided_munitions`, a country that fields ICBMs counts its silo factor at 0.85 instead of 0.70. The enemy is known in every reader that compares two countries (the `_vs_saved`, `_vs_issuer`, `_vs_target` and `_main` families, and the salvo's `nd_counterforce_destroyed_raw` / `_saved_raw` through `nd_exposed_warheads_vs_saved`), so it is applied there as a multiplier on the exposed share: × (0.85 ÷ 0.70) ≈ ×1.21, with the exposed share held at 100% or less.

- **Order.** Effective survivability (readiness applied), less Nuclear Basing's warning penalty (`nd_warning_penalty_*`, −10 near a guest's host, unchanged), then the exposed share, then the accuracy multiplier.
- **Effect.** A full triad with missile defense goes from 17.9% to 21.7% exposed. A silo force without submarines goes from 35.7% to 43.4%. The rival's precision weapons therefore push a silo power to sea, or to Launch on Warning, which is the incentive in §2.
- **Both effects stay, and each is shown on its own line** (owner call 10). The counterforce ratio keeps its +0.5 for Precision-Guided Munitions (`nd_k_ratio`): each landed warhead destroys more. The silo factor says more of a silo force is within reach. They count the same advance twice only against a silo force, the historically right target.
- **Both become modifiers**, so the technology's own tooltip and every breakdown can name them. They are numeric types that script reads (registered in `common/modifier_type_definitions/`; `modifier_field_audit`):
  - `country_nd_k_ratio_add`. `nd_k_ratio` becomes 1 + its sum: +0.5 from the Precision-Guided Munitions technology, and +0.5 from fielded ICBMs through the entry's declared modifier (§4.2). `nd_k_ratio`'s technology reads go.
  - `country_nd_silo_penetration_add`, +0.15 on the technology. The readers take it from the enemy: our silo factor against it is 0.70 + its penetration.
- **Where each is shown:**
  - The Precision-Guided Munitions technology's tooltip, both lines.
  - Survivors' hover, our side. "What its arsenal could destroy" breaks into the rival's believed warheads × its counterforce ratio, with the ratio's parts. When it has the technology and we field silos, a line says its precision weapons leave our silos more exposed (×1.21).
  - The Strike section's Forces preview, their side. Our counterforce ratio with its parts, and the same silo line when they field silos and we have the technology.
  - Delivery and Defence: our counterforce ratio with its parts, beside the attack and defense ratings.
  - The crisis's survivors lines (§5.3), whenever the silo line applies.
- **Script.** The multiplier, (0.70 + the enemy's penetration) ÷ 0.70, can't be a parameterized script value. It is written once per enemy scope the readers already save (`scope:nd_sv_enemy`, `scope:nd_issuer`, `scope:nd_target`, the main rival), beside the warning penalties, which follow the same shape.

## 4. Delivery projects

### 4.1 The mechanism

Once a programme's first device is done, The Programme section gets a **Focus**: Warheads, ICBMs or Missile Submarines (a project only while its requirements hold and it isn't fielded). Funding builds whatever the focus is. Switching is free, at any time, and each project keeps its progress while another is in focus (owner call 2; CLAUDE.md, avoid micromanagement).

- **Rate and size.** A project progresses at the first device's rate: funding × (1 + `country_nuclear_program_progress_mult`) a month, toward 100. At 5 funding steps it takes 80 weekly pulses, about 18½ months (the weekly step adds a quarter of the monthly figure, so a calendar month gains 52 ÷ 48 of it), ten warheads' worth of effort at the series rate (5 steps, a warhead every 8 weeks). The multipliers apply as they do to warheads: program aid doubles it, sabotage and UN inspections slow it, The Bomb Has Been Used speeds it.
- **One live bar.** The native bar keeps reading `nuclear_weapon_program_progress`, the progress of what is in focus. Each project's progress waits in its own variable while it isn't (`nd_proj_icbm_progress`, `nd_proj_sub_progress`). A focus change parks the live figure in the old stage's slot and loads the new one's. The bar's goal is fixed at activation (current value + 100), so the entry's `immediate` still zeroes the live variable, after parking it, and the weekly pulse loads it back, as `nd_custody_restore_progress` already does for a revolution. Warheads' own parked slot is `nd_proj_warhead_progress`.
- **Completion.** At 100 the leg is fielded (`nd_icbms_fielded`, `nd_subs_fielded`, both country variables), the focus returns to Warheads, and the rest of the week's progress is dropped (under one week's worth). Nothing past the 3-warheads-a-week cap applies to a project.
- **What holds a project.** A Nuclear Program Freeze article, a crisis freeze (`nd_crisis_programme_freeze`), the Nuclear Disarmament article, a dismantling under way and lost standing (no programme) hold projects as they hold warheads. **Arsenal ceilings and the AI's stockpile cap limit warheads only**, so they don't hold a project in focus: our own ceiling, a Nuclear Arms Limitation ceiling, the UN Prohibition Treaty's ceiling (`nd_taboo_programme_should_be_held` and `nuclear_program_ai_at_stockpile_cap` gain "and the focus is Warheads") and the funding they zero. When a project finishes under one, the focus returns to Warheads and the hold applies again.
- **The world.** Fielding a leg is public. Its rivals, the countries believed armed and its neighbors get a notice (one event per leg; the first in the world gets the headline). Deployment writes nothing on the nuclear taboo's ledger: it isn't use.
- **Development events** (test failures, a lost submarine) are left for later (§10); the first device's events are the template.

### 4.2 ICBMs

**Requirements:** a programme (`nuclear_program_has_programme`), the first device done, the `ICBMs` technology, not fielded.

**Fielded ICBMs** (`nd_fields_icbms`, one trigger, read by everything below):
- reach to every state (`nd_state_in_reach_of`, `nd_reaches_country`, `nd_reach_limited`; `nd_reach_refresh` skips the list);
- the silo factor, 0.70 (§3.1), and the accuracy multiplier against them (§3.4);
- Launch on Warning (with Radar) and Automatic Retaliation (with Radar and Mainframe Computers);
- silo accidents: the incident unit (`nuclear_incident_events.txt:1134`) and the silo explosion's weight (`:1399`);
- a modifier declared on the entry, `nd_icbm_force` (`scaling_modifiers_while_active`, value 1 while fielded, 0 otherwise). It carries +0.5 nuclear attack success, moved off the technology (owner call 1), and +0.5 to the counterforce ratio (`country_nd_k_ratio_add`, §3.4). Being declared, it follows the variable: a revolution's winner keeps it (variables carry over, modifiers don't), and nothing adds or removes it. `nuclear_strike_attack_rating` reads the modifier, so the strike odds follow; the Delivery and Defence line (`nuke_attack_line_icbms`, `zzz_extra_custom_loc.txt:118`) reads the trigger.

**Stays on the technology** (knowledge, not hardware): a Major Power's standing to run a programme (`nd_taboo_has_programme_standing`, which a project can't stand in for, since only a country with a programme can run one), the Limited War law, `country_icbm_pb_principles_bool`, +10 diplomatic play maneuvers, the aggressor escalation, the headline, the world's technology spread (`global_tech_spread_script_value`), covert theft and the research commons.

### 4.3 Missile submarines

**Requirements:** a programme, the first device done, `advanced_submarine_technology` and `guided_missiles` (a submarine needs a missile to fire), a coastal state, not fielded. ICBMs are not required: a naval power may go to sea first.

**Fielded missile submarines** (`nd_fields_missile_submarines`: the variable and a coastal state):
- reach to every coastal state;
- the submarine factor, 0.50 (§3.1);
- the submarine as the unit of the cut-off commander incident (`nuclear_incident.20`, `nuclear_incident_events.txt:1130`): harder to destroy, harder to recall;
- upkeep, the most expensive leg: `nd_upkeep_units_submarines`, first value `nd_upkeep_size_factor × 6`, a figure to tune in play-testing (owner call 11), added in `nd_upkeep_units`, shown in the upkeep breakdown and the focus preview.

**Losing the coast.** With no coastal state the leg's effects lapse and `nd_subs_fielded` stays, so they return with a coast (no rebuild for a port lost in a war).

**Stays on the technology:** the Nuclear Submarine ship type (an attack submarine), its production methods and the AI's naval strategy.

### 4.4 Saves in progress, custody and revolutions

- **Migration.** Once, under a global flag (`nd_delivery_migrated`) set on the first monthly pulse after the update: every country with the `ICBMs` technology gets `nd_icbms_fielded`, and every country with Advanced Submarine Technology and a coastal state gets `nd_subs_fielded`, armed or not, so no arsenal loses reach mid-game. A landlocked country loses its submarine reach and factor: that was the bug.
- **Revolutions.** The legs are country variables, so a revolution's winner keeps them: the winner continues the nation. Rebels who seize warheads at the outbreak (`nuclear_custody.1`) get none (owner call 3). Project progress carries over the same way and comes back through the parking in §4.1.
- **Custody and annexation.** Warheads handed to whoever holds the old capital's region arrive without delivery (owner call 3). The new holder's own legs carry them.
- **Formation.** A formed country is the same country under a new tag; its variables stay.
- **Demotion.** A power that loses its standing keeps its legs; its projects stop with its programme and keep their progress.
- **Disarmament and renunciation.** The Nuclear Disarmament article's `on_entry_into_force` and the end of a dismantling remove both legs (owner call 9: disarmament treaties took launchers too, so a renounced country that resumes rebuilds its delivery). Every path that removes a leg re-checks the launch authority's gate and falls back to Central Authorization (`nd_set_authority_1`), putting `nd_authority_months` back as it was, since the government didn't choose the change (the No-First-Strike amendment's binding does the same for doctrine).

### 4.5 The AI

The AI sets its focus in its posture review (`nd_ai_review_posture`, every sixth month and when a crisis opens), not through buttons: the review already sets the rest of its posture by script.

**The range score** (owner call 12). Range is worth more than warheads to the degree that the bombers reach nobody who matters. `nd_ai_range_score`, from 0 to 1, weighs the countries the AI must be able to strike: a rival, a war enemy or a crisis opponent 3, an antagonistic country believed armed 2 (first values). It is the weighted share of them out of bomber reach (`nd_reaches_country` false), and 0 when there are none.

**Range** means the ICBM project, unless missile submarines are available and every out-of-reach country that matters has a coast. In that case it means the submarine project, which also buys survival.

1. **Range first** when the score is 1. No country that matters is in bomber reach, so a warhead deters nobody until it can fly.
2. **Warheads** while it holds fewer than half its desired stockpile (`nuclear_ai_desired_stockpile`). At war or in a crisis with a country out of reach, it builds range instead.
3. **Range** when the score is 0.5 or more.
4. **Missile submarines** when available and either it is vulnerable to its main rival (`nd_ai_vulnerable_to_main_rival`: fewer than three survivors at Heightened with no launch credit), or the rival has Precision-Guided Munitions and it fields silos.
5. **Range** when the score is above 0.
6. Otherwise **Warheads**.

When 3 and 4 both hold, a war or crisis with an out-of-reach country puts range first; otherwise submarines. A score of 0 never builds range: that is the India–Pakistan rule. Each review logs the score and the focus it chose in a new `TE_NUCLEAR: type=ai_focus` line, for observer balancing.

**Funding.** The increase button's `ai_chance` (`common/scripted_buttons/nuclear_program_buttons.txt`) gets +35 while a project is in focus, as a shortfall under the desired stockpile does, and the decrease button's two stockpile terms (+35 at the desired stockpile, +15 above it) don't count while a project is in focus. Without this an AI at its desired stockpile defunds the programme and never fields anything, and AI great powers stay bomber-bound for the whole game.

## 5. What the player sees (owner call 8)

### 5.1 The rule

Every value a decision rests on is shown where the decision is made, in the units of its outcome, on the panel or one hover away. A choice shows what it changes, not only what it is called. Numbers live in script values and reach the panel through them; nothing is restated in `.gui` or loc (`docs/guides/gui_style_guide.md`, and the widget's editing rules in `docs/systems/journal_entry_systems.md`). A figure in a hover is a numeric display modifier or a script value, never words in a boolean's name (`.claude/rules/script.md`).

### 5.2 Hidden on purpose, and the world's view

**Hidden:**
- **Another country's true arsenal.** The world sees `nd_shown_public_estimate`, never the stockpile, in any figure, hover, loc splice or chart (owner rule; `mod_systems/nuclear.md`, National Info; `test_nuclear_layout.py`'s `PrivateTest`).
- **Outside a crisis, another country's readiness, survivability, safeguards, hardening and command reliability.** Inside a crisis the danger breakdown already gives each side the other's readiness and the threatening side's command reliability (`nd_cd_*_line`, `te_miscellaneous_l_english.yml:5182–5187`; `nuclear_deterrence_values.txt:1330–1367`), and the more vulnerable side's effective survivability below 50 (`:1426`). That stays.
- **Chance itself.** Incident rolls, a strike's roll and attribution are random: their odds are shown, not their outcomes.
- **The AI's weights.**

**Public:** doctrine and launch authority (owner, rework spec §14.2), technologies, and the fielded legs (§2). The leak test still lists `nd_authority` as private (`TRUE_VARS`, `test_nuclear_layout.py:1201`). Phase 1 takes it off that list, citing the owner's ruling, and shows another country's authority beside its doctrine.

**The world's view of another country** is what every preview of it reads:
- its shown public estimate (`nd_shown_public_estimate`, which is 0 until seeded; never `nd_believed_stockpile`, which falls back to the live count, `nuclear_deterrence_values.txt:2614–2633`);
- its doctrine, authority, technologies and fielded legs, and so its survivability target;
- its readiness from the crisis panel in a crisis, else Heightened;
- its safeguards unknown.

The target is an upper bound: a force that stops hardening decays toward 30% of it. Unknown safeguards can cut a fast authority's credit by up to 0.15 (`:747–757`). So a preview prints a range: against a force at its target with full credit, and against one at its floor with the credit cut by 0.15.

**Every such figure says so** (owner call 14). On the figure: a short qualifier, "up to" for what survives, "at least" for what a strike destroys, or the range itself. In its hover, one shared explanation (`nd_tt_worlds_view`): what we don't know (their hardening and safeguards), what the figure assumes (forces as secure as their technology allows), and what the other end of the range assumes. A single figure the script uses (crisis pressure, the AI) takes the cautious end, and where the panel shows it, it carries the same qualifier and hover.

**Where the code reads more than the world's view today.** Both move to the world's view in phase 1 (owner call 13):
- When one side's crisis pressure counts the other side's survivors, it reads the other side's true state (`nd_yp_issuer_exposure_line`; `nuclear_deterrence_values.txt:1479–1533`). The opening preview's "survivable" line reads the target's true survivors (`nuclear_crisis_effects.txt:189–206`). A side's own survivors are its own to know, and stay true.
- `nd_redundancy_believed`, which the AI's Leadership planning reads, adds the target's true survivability ÷ 20 (`nuclear_deterrence_values.txt:801`). It also reads `nd_believed_stockpile` and its live-count fallback.

### 5.3 Inventory: each decision and what it rests on

"Today" is what the panel shows as of this spec, checked by the audit in §5.5.

| Decision | What it rests on | Today | This spec |
|---|---|---|---|
| Programme focus (new) | Each option's progress and months to finish at current funding; what it grants (reach, the survivability target before and after, the counterforce ratio, the authorities it unlocks, attack success, upkeep); warheads not built meanwhile; what holds it | — | The Focus rows (§5.4) |
| Programme funding | Innovation cost, progress a month, time to the next warhead or to the project's end, what holds funding | Stepper, cost, rate and its sources, time to next warhead | The rate and time follow the focus |
| Hardening | Cost a week; survivability now, its target and floor; this month's step; how fast the gap closes | Cost; the bar with the ceiling line (`nuclear_deterrence_widget.gui:2096`) and the rise or fall still to come; the floor never printed (`nuclear_deterrence_values.txt:2319–2348`); the stepper says only "climbs faster" (`te_miscellaneous_l_english.yml:5703`) | The target line; the floor printed; each level's hover gives this month's step and the months to close half the gap (about 34, 17 and 11 at levels 1–3: constants, since script values have no logarithm, pinned to the 2% rate by a test) |
| Safeguards | Cost; reliability target; chance of a halt; the launch credit each level takes away | Cost; reliability and halt rows; the credit cut as a modifier line; the stepper says only "improves over the coming months" (`:5705`); the +12 reliability target and +5 halt chance a level (`nuclear_deterrence_values.txt:243`, `:534`) printed nowhere | Both per level, and the warheads a full strike would destroy at the new level |
| Launch authority | Launch credit; warheads a full strike by the main rival would destroy; the chance of a halt; whether a warning reaches the government; the cut-off commander's eligibility; decapitation immunity and our own command redundancy; custody loss; upkeep | Modifier lines (credit, immunity, unapproved launches, −10 halt under Launch on Warning, custody loss); Automatic Retaliation's upkeep (`te_miscellaneous_l_english.yml:5602`); Central's three-quarters rule in words (`:5834`). Not shown: our command redundancy as a number (only the concept's formula, `te_concepts_l_english.yml:763`), the halt chance under each option, the warheads saved | Each option's hover adds the warheads lost to a full strike under it and the halt chance under it; Central's adds our command redundancy. Incident exposure has no authority term (`nuclear_deterrence_values.txt:422–433`), so it isn't shown per option |
| Readiness | Upkeep; the survivability a crisis counts; incident exposure; crisis danger | Upkeep and counted survivability per level; modifier lines | Each level adds the warheads lost to a full strike |
| Doctrine | Strike gates, taboo and infamy costs, interest-group views | Modifier lines, the taboo section's costs, At Home | Unchanged |
| Arsenal ceiling and dismantling | Warheads held, the world's estimate, tighter ceilings, the burden and upkeep at the new size, restraint groups' easing | Arsenal rows; today's burden and the size at which restraint groups ease (`te_journal_entries_l_english.yml:1038`; `te_miscellaneous_l_english.yml:5484`) | The stepper's hover adds the burden and upkeep at the next size, and says a ceiling holds warheads only, not a project |
| Strike: Cities | Warheads expected to land, deaths, the share of buildings razed, taboo, infamy, UN record | The mission's hover is words only (`:6007`). The Launch Order gives one warhead's infamy and relations cost and the √ rule (`:5555`). The odds and the razed share are shown only for the single-city diplomatic action (`extra_effects.txt:752–754`) | Expected landed, deaths and razed share for the salvo as set |
| Strike: Forces | Warheads the salvo would destroy, how many would fly first under their launch authority, what survives to answer | Words only (`:6009`) | The range (§5.2) of destroyed, flown first and their survivors, at the salvo size set |
| Strike: Leadership | Decapitation chance at the salvo size, their command redundancy | Words and the rule ("three in four when twice as many land", `:6011`) | The chance at the salvo size set, from the world's view of their redundancy |
| Opening a warning or ultimatum (added) | The pressure and danger it would open at | The preview gives pressure factors as ranges ("up to −25", `:5725–5733`), no starting total and no danger figure | The starting pressure and danger totals |
| Crisis moves | Pressure and danger by part, survivors on each side, follow-through, what each move changes | Both breakdowns and follow-through. Survivors appear only as pressure points that stop changing at three survivors (`nd_yp_answer_line`, `nd_yp_issuer_exposure_line`, `:6058`, `:6065`). Go public's +10 danger and its move to stage 2 aren't in its hover (`:5580`, `:5671`) | The survivors behind those parts printed beside them, the accuracy multiplier when it applies; Go public's hover gives its danger and stage change |
| Launch under attack (`nuclear_incident.1.c`, added) | Our survivors against the suspect if we wait; the price of a first use if the warning is false | Words only (`:5692`). Our survivors against the suspect are computed (`nuclear_deterrence_effects.txt:1717`) but read only by the AI's chance | Both figures in the option's hover |
| Disavow our strikes (added) | The chance the victim believes us; the price of a lie found out | Words only (`:5921`) | Both: the chance from `nd_claim_belief_value` (`nuclear_deterrence_values.txt:2206`), the price from the script values it already applies |
| Nuclear Basing and Nuclear Guarantee articles (added) | −10 survivability against the guest for the host's neighbors (`nuclear_deterrence_values.txt:849`); a third of the guest's accidents in the host; the −10/−20 pressure a guarantor gives (`:1539`); the cost of leaving | Words only (`te_concepts_l_english.yml:2151`, `:2167`) | The figures in the descriptions, from the script values |
| Others' delivery (new) | Which legs each armed country fields, hence whom it can reach | The Reach row lists whom we reach by bomber | A delivery column in Nuclear Powers, a row in National Info's public view |

### 5.4 Panel changes

- **The Programme** (`nuclear_program_widget.gui`).
  - A Focus subsection, open, shown from the first device on: three choice rows (`nd_choice_row`, the option in focus tinted), each greyed with its missing requirement and showing its progress and months to finish.
  - Each row's hover lists what fielding it grants as modifier lines. The ICBM row prints `nd_icbm_force`'s own lines, attack success and the counterforce ratio (§4.2). The rest use display-only numeric types: `country_nd_exposure_mult` for the factor and `country_nd_upkeep_units_add`. Booleans are only for rules without a quantity, such as reach to every state and the authorities it unlocks. The hover then gives the survivability target before and after, the countries in reach before and after, and the warheads the months in focus will not build.
  - The handler is `nuclear_program_focus_sgui` (ops 1 Warheads, 2 ICBMs, 3 Missile Submarines), with `ai_is_valid = { always = no }`. Its op table goes in the sgui header, the `.gui` header and `journal_entry_systems.md`.
- **Forces** (`nuclear_deterrence_widget.gui`).
  - **Survivability.** The ceiling line becomes the target line and the floor is printed. Its hover already gives the readiness factors and the effective figure (`te_miscellaneous_l_english.yml:6025`). The hover then adds the chain: one line per part with its factor and whether it is held, then the exposed share and the target.
  - **A new Launch credit row** after Survivors: the share, with a hover naming the authority's credit and each safeguards level's cut.
  - **Survivors.** Today it is refreshed monthly and in the AI review (`nd_refresh_main_rival`, `nuclear_deterrence_effects.txt:451`, `:523`, `:3729`). It now also refreshes on every posture op, so it follows a click. Its hover adds the accuracy multiplier line when the main rival has Precision-Guided Munitions and we field silos.
  - **Reach.** The row is hidden today once ICBMs are researched (`nd_reach_limited_sgui`, `nuclear_deterrence_sguis.txt:440–446`). It is shown while armed instead, reading "every country" with ICBMs and "and coasts" with fielded submarines (`nd_reach_value`).
- **Posture.**
  - Each launch authority option's hover adds "a full strike by <main rival> would destroy N of our M" and the halt chance under it. Each readiness row adds the same strike figure.
  - The GUI can't take the rival from a variable as a scope (`gui_modding_guide.md` gotchas #11 and #15), so `nd_refresh_main_rival` stores these figures, one per option, as it stores `nd_survivors_main`.
  - That needs exposure values per readiness (only `_r2_vs_saved` exists, `nuclear_deterrence_values.txt:895`) and a launch credit per authority (`nd_launch_credit` reads the authority in force, `:739`).
- **Strike.**
  - The Cities, Forces and Leadership previews are stored on every planner op in `nd_plan_refresh`, which already runs then and weekly. A scripted GUI that saves a temporary scope is the other route; the self-check `nd_trigger_temp_scope` (`nuclear_deterrence_effects.txt:1094–1113`) tests it.
  - The formulas exist: destroyed and flown first (`nuclear_deterrence_values.txt:1033–1059`), decapitation (`:1070–1088`).
  - Warheads expected to land: the sum of the per-state odds over the states the mission would pick, picked by the salvo's own picker and the marks cleared after. If that picker can't run outside the salvo, fall back to the capital's odds for every warhead, as the AI does (`nd_ai_capital_hit_share`, `:1184`).
  - Each preview is labelled an estimate.
- **Crisis.** The survivors beside the pressure parts that count them; Go public's danger and stage change in its hover; the opening preview's starting totals.
- **Events.** `nuclear_incident.1.c` and the disavowal's figures, through `custom_tooltip` lines on the options.
- **Treaty articles.** Nuclear Basing's and Nuclear Guarantee's descriptions take their figures from the script values.
- **Nuclear Powers and National Info.** A delivery column (bombers, ICBMs, submarines as icons) and the launch authority for each listed country; another country's National Info public row shows both. `PrivateTest` lists the leg variables and `nd_authority` as public.
- **Help page.** The programme topic explains the focus; the posture and forces topic explains the chain and launch credit.

### 5.5 Visibility audit (2026-11-20)

A separate agent read the code against the first draft of §5, without its conclusions, as owner call 8 asks. Its findings are folded into §§5.2–5.4 above. Each was checked in the code before it went in. In summary:

- **Corrected "Today" cells:**
  - Strike: Cities (no odds or razed share for a salvo);
  - Crisis moves (no survivors figure, only pressure points);
  - Launch authority (upkeep and the three-quarters rule already shown; redundancy and the halt chance not);
  - Hardening (ceiling line, no floor);
  - Safeguards (their per-level figures unprinted);
  - Survivability's hover (it already shows readiness);
  - Reach (hidden once ICBMs are researched);
  - Survivors (monthly refresh).
- **Decisions added:** opening a warning or ultimatum, launch under attack, Go public, Disavow our strikes, the Basing and Guarantee articles, and the arsenal ceiling's next size.
- **§5.2 changes:**
  - readiness is private only outside a crisis;
  - launch authority is public but the leak test lists it as private;
  - two existing reads go past the world's view (since answered: owner call 13);
  - previews show a range, because the target is an upper bound and safeguards are unknown.
- **Feasibility changes:**
  - the per-option strike figures are stored by `nd_refresh_main_rival`, not computed in the GUI;
  - "incident exposure per authority" is replaced by the halt chance, since exposure has no authority term;
  - hardening's "months to within 5" is replaced by half-gap constants, since script values have no logarithm;
  - the Strike previews' expected landed count is decided;
  - the draft's question on the AI's planning is restated, since that planning already reads the world's view apart from the redundancy leak (since answered: owner call 13).
- **Unverified:** whether a GUI `ScriptValue` with `AddScope` can take a scope read out of a variable in this panel. The design doesn't rely on it (the stored figures above).

## 6. Tooling and tests

- `scripts/analysis/nuclear_survivors.py` and `test_nuclear_survivors.py` mirror the product, the accuracy multiplier and §3.3's table.
- **A technology-read guard** (new test, `test_nuclear_delivery.py`): outside an allowlist of the knowledge sites in §4.2 and §4.3, nothing in `common/`, `events/` or `gui/` reads `has_technology_researched = ICBMs` or `= advanced_submarine_technology`; delivery reads go through `nd_fields_icbms` / `nd_fields_missile_submarines`. It also pins the holds that exempt a project (§4.1), the migration's single run and the AI's focus order.
- `test_nuclear_reach.py`: the reach triggers read the two delivery triggers.
- `test_nuclear_deterrence.py`: the new handler's op table.
- `test_nuclear_layout.py`: the new public rows read only public variables (`PrivateTest`, `ObserverTest`), and `nd_authority` leaves `TRUE_VARS` with the owner's ruling cited. `PrivateTest` covers another country's panel, not our own panel's reads of an enemy, so a new check holds every preview of another country (the Strike previews, the opening preview, the crisis survivors lines) to world's-view values (§5.2).
- The hardening half-gap constants (§5.3) against the 2%-per-level rate.
- The audits that apply: `je_immediate_reset_audit` (the parked progress is never zeroed in `immediate`), `silent_variable_audit` (every focus change says so in a `custom_tooltip`), `tooltip_walk_variable_audit` (the focus ops behind the click-only marker), `modifier_field_audit` (the new display types registered), `loc_coverage_audit`.

## 7. Docs and the player guide

- **Chapter 14:** "Who can run a weapons program" (unchanged rule, but the ICBM technology's role restated); "Program funding and warhead production" (the focus and the projects, a row each in the stage table); "Range and Nuclear Basing" (reach from fielded legs); the survivability paragraph (the chain in place of the ceiling, the factors as a table); launch authority (launch credit and what it saves); the strike planner's previews. Then rebuild the PDF.
- `mod_systems/nuclear.md`, `nuclear_crisis_design.md` §0 (a new subsection per phase), `journal_entry_systems.md` (the widget areas and op tables; that file is CRLF), `docs/testing/nuclear-playtest.md`.
- Loc in American English through the `event-text` skill; `organize_loc.py` after new keys.

## 8. Engine facts and in-game checks

No new engine fact is load-bearing: script values, declared modifiers on the entry, `is_coastal`, choice rows and the parked-progress pattern are all already used in this system. The play-test list (`docs/testing/nuclear-playtest.md`) gains:

- A focus change mid-project: the bar shows the new stage's progress at once, and the old one's comes back when switched back.
- A re-activation (rank lost and regained) with a project in focus: the bar's goal stays at 100 and the progress returns the next week.
- A project finished under an arsenal ceiling: the focus returns to Warheads and the hold resumes.
- An AI great power at its desired stockpile with a distant rival: it funds and fields ICBMs.
- A landlocked armed country after migration: no coastal reach.
- A posture click: the Survivors row and the per-option strike figures follow it the same day.
- The Strike previews against the salvo that follows: the expected landed count and the destroyed range hold the outcome.
- The submarine leg's upkeep against the other legs' and the arsenal's other costs (owner call 11).
- An observer game's `type=ai_focus` lines: powers whose rivals are all in bomber reach build warheads, distant rivals bring ICBMs, small exposed arsenals go to sea (§2, §4.5).

## 9. Phases

1. **Survivability and display** (no projects yet). §3 in full; `nd_fields_icbms` and `nd_fields_missile_submarines` introduced, reading the technologies (the submarine trigger also asks for a coastal state, fixing the landlocked bug), with every delivery read routed through them and the guard test; every §5 change that needs no project (Forces, Posture, Strike, Crisis, the events, the articles, launch authority public) and owner call 13's world's-view fixes. Player guide and docs.
2. **Delivery projects.** §4: the focus, the two projects, the triggers reading the fielded variables, the attack-success move, the holds, the migration, upkeep, the notices, the AI; §5.4's Programme, Nuclear Powers and National Info changes; the play-test list.
3. **Later, separate specs** (§10).

## 10. Later

- **Thermonuclear weapons:** a third project on the same focus, unlocked by an era-7 technology from `nuclear_weapons` that unlocks nothing else. Its payoff is strategic: the counterforce ratio and crisis credibility, at most a modest rise in a city strike's deaths, and a public test that seeds the world's estimate, writes the taboo's ledger and risks a fallout event. That test is the hook for a Partial Test Ban article, an arms-control lever on quality rather than count.
- **Strategic defense:** the owner's example for call 1's later modifiers. It can't live on the programme's bar, which only a country with a programme has, while missile defense matters most to countries without one. It needs a home of its own, beside the military base's Missile Defense production methods and the orbital battlestation.
- **Development events for the projects**, on the first device's pattern.

## 11. Open questions

None. The draft's five were answered by the owner on 2026-11-20 and are §1's calls 9 to 13. Two more figures are left to play-testing on purpose: the submarine leg's upkeep (call 11) and the range score's weights (§4.5).
