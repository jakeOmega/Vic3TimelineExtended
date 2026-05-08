# Future Journal Entry Ideas

This document sketches ideas for new journal entries inspired by the mod's technology tree (Eras 7–12) and existing systems. Each entry outlines the core concept, trigger conditions, key mechanics, success/failure states, and event flavor.

**Implementation status:** All 8 JEs below have MVP implementations (JE definition, 2 monthly pulse events, 1 fail-state event, modifiers_while_active, completion/fail/timeout modifiers, full localization). See `docs/systems/mod_systems.md` § "Social Movement Journal Entries (MVP)" for the file index and summary table. Planned expansion includes additional events (5-6 per JE), scripted toggle buttons, and cross-JE interactions.

---

## 1. LGBTQ+ Rights Movement

**Trigger tech:** `LGBTQ_rights_movement` (Era 9)
**Prerequisite:** Country has `civil_rights_movement` researched, has pops of certain discrimination statuses or specific laws (e.g. `law_no_womens_rights`, `law_outlawed_dissent`)

### Concept
A social movement demanding legal recognition and equal treatment for LGBTQ+ citizens. Mirrors the civil rights JE structure but focused on a different axis of discrimination.

### Key Mechanics
- **modifiers_while_active:** Small turmoil increase + civil rights political movement attraction increase. Note, we need to add LGBTQ+ law friendly stances to the civil rights movement.
- **Status descriptions** gated on LGBTQ+ rights law group
- **Monthly pulse events** (5–6 events):
  - Pride march / parade (allow, suppress, co-opt for tourism)
  - Religious backlash (devout IG demands crackdown, player chooses)
  - Military service debate (allow openly LGBTQ+ soldiers, don't ask / don't tell, ban)
  - Celebrity coming out (media figure, provokes culture war, options to celebrate or censor)
  - Hate crime incident (investigate, ignore, use as political leverage)
  - International LGBTQ+ advocacy (foreign pressure similar to civil rights event 4)
- **Toggle buttons (optional):** None needed.

### Success State
Enact progressive LGBTQ+ legislation (e.g. full legal protection law). Rewards: prestige, loyalists among academics and middle strata, acceptance boosts, decaying modifier for international reputation.

### Failure State (Oppressive Win)
Movement crushed under criminalization laws. Event with law-gated options:
- Criminalization: Boost authority, increase secret police effectiveness (if secret police enacted), reduce turmoil but costs prestige.
- Tolerance (movement just fizzled): Minor radicals among progressives.

### Timeout
Social tension festers — radicals among both upper and lower strata. No one is happy with inaction.

---

## 2. Second-Wave Feminism / Gender Equality

**Trigger tech:** `second_wave_feminism` (Era 7)
**Prerequisite:** Country does NOT have full women's rights (e.g. not `law_protected_class`), potentially also based on `lawgroup_family_reproductive_policy`.

### Concept
A sustained movement pushing beyond basic suffrage into workplace equality, reproductive rights, and cultural representation. Distinct from vanilla women's suffrage JE — this is about the second wave (1960s–80s style).

### Key Mechanics
- **modifiers_while_active:** Small boost to political movement attraction, small bureaucracy penalty (policy debates).
- **Status descriptions** gated on women's rights law group
  - No rights → Suffrage only → Full equality
- **Monthly pulse events** (5–6 events):
  - Equal pay protest (wave of strikes in factories/offices, options: enforce equal pay mandate, suppress, study the issue)
  - Reproductive rights debate (contraceptive pill tech synergy — legalize contraception, restrict, make it state-subsidized)
  - Glass ceiling incident (prominent woman denied promotion in government/military, promote her, quietly settle, publicly side with status quo)
  - Women in the military (allow combat roles, support roles only, ban entirely)
  - Feminist literature boom (fund, ban, ignore — cultural effects)
  - Backlash from traditionalists (devout/landowners IGs push back, handle tension)

### Success State
Enact the most progressive women's rights law. Rewards: prestige, worker productivity bonuses, loyalists among academics and middle strata.

### Failure State (Traditionalist Win)
Movement collapses under restrictive laws. Event: entrench traditional gender roles (boost authority, loyalists among upper strata and devout).

### Timeout
Stagnation — radicals among educated pop types, prestige penalty.

---

## 3. Human Augmentation Debate

**Trigger tech:** `biohacking_and_human_augmentation` (Era 11) or `brain_computer_interfaces` (Era 11)
**Prerequisite:** Country has the tech researched.

### Concept
Society is forced to confront fundamental questions about human identity as augmentation technology becomes widespread. Not a simple progress-vs-tradition binary — there are economic, military, ethical, and class dimensions. Needs to tie into `lawgroup_human_augmentation`.

### Key Mechanics
- **modifiers_while_active:** Research speed bonus (augmentation drives innovation) + turmoil (social disruption).
- **Scripted toggle buttons** (2–3 toggles, like banking cycle):
  - **Augmentation Subsidies** (ON/OFF): When ON, boosts innovation/throughput but costs treasury. When OFF, only elites can afford augmentation (class tension).
  - **Military Augmentation Program** (ON/OFF): When ON, boosts military quality but costs maintenance. Synergy with `bioenhanced_soldiers` tech.
  - **Augmentation Ethics Board** (ON/OFF): When ON, reduces turmoil and radicalism but slows research. When OFF, biohacker underground events fire more often.
- **Monthly pulse events:**
  - Augmentation divide deepens (rich enhanced vs. poor natural — wealth inequality angle)
  - Workplace discrimination (unaugmented workers fired, union response)
  - Augmented crime wave (enhanced criminals, police debate)
  - Religious condemnation of "playing God"
  - International augmentation arms race
  - Black market implants (safety crisis)
- Uses existing transhumanist movement events (9–12) plus new ones.

### Success State
Society integrates augmentation equitably (requires subsidies + ethics board active for X months, or specific law). Rewards: permanent throughput/innovation bonuses, prestige, stability.

### Failure State (multiple paths)
- **Unregulated path:** Class war between augmented and natural humans. Revolution risk, massive radicals.
- **Banned path:** Brain drain — research talent emigrates, research penalty, slight stability.
- **Military-only path:** Military grows powerful, authority increases, civil liberties decrease.

### Timeout
Augmentation divide becomes permanent feature of society — ongoing class tension modifier, no resolution.

---

## 4. Environmental Crisis Response

**Trigger:** Global warming JE already exists, but a **separate** JE for the *pollution response* would complement it.
**Trigger tech:** `environmental_movement` (Era 8) or maybe `pollution_control` (Era 7)

### Concept
Not about the physical climate (that's the existing GW JE), but about the political battle over pollution - think clean air act, etc.. An environmental movement demands action; industry demands business-as-usual.

### Key Mechanics
- **modifiers_while_active:** Enactment time reduction for environmental laws (political pressure accelerates action).
- **Scripted toggle buttons:**
  - **Green New Deal** (ON/OFF): Massive investment in clean industry, costs treasury but reduces warming contribution, requires green energy tech.
  - **Industry Protection** (ON/OFF): Shield polluting industries, gains industrialist support but accelerates warming, boosts pollution.
  - Others?
- **Monthly pulse events:**
  - focus on pollution incidents (oil spill, smog crisis, water contamination) and political responses (protests, lobbying, international pressure).
  - Eco-terrorism incident (radical fringe)

### Success State
Country passes comprehensive environmental legislation (high enough institution level for the existing ministry of the environment?). Rewards: prestige, innovation bonuses, green industry throughput.

### Failure State
Environmental movement collapses, industry wins. Short-term economic bonus, accelerated warming contribution, higher pollution, stronger industrialists IG.

### Timeout
Political paralysis — neither side wins, continued damage.

---

## 5. Digital Rights & Surveillance Debate

**Trigger tech:** `automated_surveillance` (Era 9) or `cybersecurity` (Era 9)
**Prerequisite:** Country has a certain level of technology.

### Concept
As digital surveillance becomes ubiquitous, a movement emerges demanding digital privacy rights. The state must balance security against liberty. Needs to tie into `lawgroup_privacy_rights`, `lawgroup_ministry_of_intelligence_and_security`, `lawgroup_right_to_information`, etc.

### Key Mechanics
- **modifiers_while_active:** Authority bonus (surveillance is tempting) + turmoil (privacy backlash).
- **Scripted toggle buttons:** None needed
- **Monthly pulse events:**
  - Whistleblower reveals surveillance (à la Snowden)
  - Hacker collective attacks government systems
  - Social media censorship debate
  - AI-powered predictive policing controversy
  - Data breach exposes citizens' private information
  - Foreign cyber-espionage discovered

### Success State
Pass digital rights legislation or dismantle surveillance apparatus. Rewards: prestige, innovation boost (tech talent stays), loyalists among intelligentsia.

### Failure State (Security State Win)
Full surveillance state established. Authority skyrockets, innovation stagnates (brain drain), prestige collapses internationally but domestic turmoil is suppressed. Fairly strong outcome short-term, but tech lag is dangerous long-term.

### Timeout
Uneasy status quo — surveillance continues without legal framework, periodic crises.

---

## 6. Post-Scarcity Transition

**Trigger tech:** `post-scarcity_economy` (Era 12) or `universal_basic_income` (Era 10) for an early version
**Prerequisite:** Extremely advanced economy.

### Concept
As automation and AI make traditional labor obsolete, society must decide what comes next. This is a late-game "capstone" JE about the fundamental structure of civilization. Tie to advanced `lawgroup_welfare` existing laws.

### Key Mechanics
- **modifiers_while_active:** massive unemployment turmoil?
- **Scripted toggle buttons:**
  - None, handle via existing laws
- **Monthly pulse events:**
  - Mass unemployment protests
  - AI replaces government bureaucrats
  - Meaning crisis (people without purpose, mental health)
  - Luxury communism debate (political movements)
  - Neo-Luddite terrorism (smashing robots)
  - Post-scarcity art renaissance

### Success State
Smooth transition to post-scarcity economy. Permanent bonuses to welfare, SoL, prestige. Game-changing late-game reward.

### Failure State
Dystopian authoritarian control where the AI-owning elite rule.

### Timeout
Permanent class stratification — augmented/AI-connected upper class vs. obsolete lower class. Turmoil.

---

## 7. Mental Health Crisis

**Trigger tech:** `mental_health_awareness` (Era 10)
**Prerequisite:** High urbanization + certain SoL thresholds.

### Concept
Modern life produces a mental health epidemic — depression, anxiety, addiction. Society must decide whether to treat this as a medical, social, or moral problem.

### Key Mechanics
- **modifiers_while_active:** Mortality increase (suicide crisis).
- **Monthly pulse events:**
  - Workplace burnout epidemic
  - Youth mental health crisis (social media connection)
  - Addiction crisis (opioids / digital)
  - Veteran PTSD wave (after wars)
  - Institutional care scandal
  - Therapy destigmatization campaign

### Success State
Establish comprehensive mental health infrastructure. Loyalists, SoL boost.

### Failure State
Crisis ignored — ongoing mortality penalty, brain drain.

---

## 10. Decline of Religion / Secular Transition

**Trigger tech:** `decline_of_organized_religion` (Era 10)
**Prerequisite:** Literacy above a threshold, certain social techs researched.

### Concept
As secularism spreads, organized religion loses its grip on society. The devout IG strengthens (backlash), and a meaning vacuum creates new tensions.

### Key Mechanics
- **modifiers_while_active:** Devout IG political strength increase (backlash) + turmoil from cultural disruption.
- **Monthly pulse events:**
  - Megachurch scandal (corruption, hypocrisy)
  - New Age / spiritual movement emerges
  - Religious hardliner backlash (terrorism, political extremism)
  - State religion debate (disestablish the church?)
  - Moral panic ("society has lost its way")
  - Interfaith dialogue initiative
- **No toggle buttons** — mostly event-driven narrative.

### Success State
Smooth secular transition — reduced IG friction, innovation boost, multicultural acceptance, long-term devout marginalization.

### Failure State
Religious revivalism — devout IG surges, regressive law enactment pressure, authority boost.

---

## Priority Ranking (suggested implementation order)

1. **LGBTQ+ Rights Movement** — Direct parallel to civil rights JE, reuses many patterns, clear tech trigger, high narrative value.
2. **Second-Wave Feminism** — Similar structure, complements vanilla suffrage JE, strong tech hook.
3. **Digital Rights & Surveillance** — Relevant to modern era, good mechanical depth with toggle buttons.
4. **Environmental Crisis Response** — Complements existing GW JE, adds political dimension.
5. **Mental Health Crisis** — Interesting mechanics (mortality/throughput), unique angle.
6. **Human Augmentation Debate** — Complex and interesting, but requires Era 11+ (late game).
7. **Decline of Religion** — Good narrative, but mechanically overlaps with existing religion system.
8. **Post-Scarcity Transition** — Capstone late-game JE, depends on many other systems existing first.
