# Grand Monuments as a political instrument — design

## Context

The Grand Monument (#256, dedication rework in #350) is one repeatable building, `building_grand_monument`
(`common/buildings/grand_monuments.txt`), with one PM group of dedications (`pmg_monument_dedication`,
`common/production_methods/grand_monument_pms.txt`), a dedication ceremony (`monument_events.1`/`.2`) and eight
flavour events (`.3`–`.10`, `events/monument_events.txt`). It was built as a construction sink: expensive
(`construction_cost_grand_monument = 10000` a level), cheap to run, uncapped, and deliberately a bad investment. The
review found:

- **It has no purpose of its own.** The payoff is 1 Tourism and +1% Tourism Industry throughput a level; the stated
  reason to build is that spare construction goes somewhere. That premise was written for vanilla construction (the
  sector's wages run whether or not points are used). Under the default construction market (#398) the state buys
  construction as a good, so whether idle capacity still costs anything is **unverified**. It no longer matters: in
  this design absorbing construction is a side effect.
- **One permanent choice, then nothing.** The dedication is picked once. The eight flavour events are single-option
  text with no effects. Nothing reacts to a monument: no interest group, no prestige (each vanilla monument gives
  +25), no tie to the regime that raised it.
- **It rewards wide, not tall, and that is an exploit.** National effects sit in `country_modifiers { unscaled }`,
  once per building, uncapped. A 40-state empire with a level-1 Grand Observatory in every state has +80 innovation
  cap for 400k construction; level-1 War Memorials everywhere give −40% war support lost to casualties; Grand Shrines,
  +80% Devout attraction. Cultural pull was capped at +5 for exactly this reason; the PM effects never were.
- **Tall is broken too.** The local effects are linear per level with no limit: a level-40 War Memorial adds +0.40
  conscription rate to its state, Botanical Gardens cancel 40,000 pollution, a level-50 Stadium reaches −100% turmoil
  effects.
- Smaller: the two law gates hide ceremony options but not the building panel's PMs; the ceremony tooltips repeat the
  PM numbers by hand (the TOOLTIP MIRROR header); all eight dedications have identical economics; the icon is
  Government Administration's.

This design keeps the building and reworks what it is for: a regime raises monuments to what it stands for, gains
prestige, legitimacy and the favour of the interest groups that share the message, and leaves a legacy the next
regime has to deal with.

Baseline: `main` at `0de90891` (#504 merged).

## Decisions (owner, 2026-09-27)

| Question | Decision |
|---|---|
| Role | **A political/legacy instrument.** Regimes build monuments for reasons and pay for them politically; absorbing construction is a side effect |
| Chassis | **Rework in place.** Keep `building_grand_monument`, one per state, levels as *grandeur*, the dedication as a PM group |
| Legacy | **Contested, with a decision.** A monument whose message stops fitting becomes contested; the owner chooses Tear Down, Rededicate or Preserve as Heritage (§4) |
| Identity | Flavour keyed to the builder's **own** culture or religion is welcome (a Temple for a Jewish state, a Hall of Dynasties for a Chinese monarchy). The line is harm: no player-picked identity as the target of a cost, no monument *against* a group |
| National payoffs | **Prestige, legitimacy, IG approval and the dedication-specific effects**, all from national totals, never per building |
| Costs | **Vanity backlash** in hard times (§5), besides construction and upkeep. No superlinear upkeep, no rival targeting in v1 |
| Where the politics lives | **A Monuments journal entry** (§6) |
| Tourism | **No Tourism output.** Local Tourism Industry throughput about **+5% a level** at first (a vanilla monument is +25%, so five levels match one) |
| Diminishing returns | **The doubling curve everywhere**: each further step costs twice the grandeur of the one before (§2.2). Preferred to hard caps; the JE shows the next step to keep it legible |
| Leader's IGs | Approved by the ruler's own IG; opposed by the strongest IG **outside** the government (not a fixed IG) |
| Gardens | Approved by the **Rural Folk** |
| Leader succession | A Leader monument is contested **on every change of ruler** (the successor's de-Stalinisation choice). Royal statues are To the Crown, so royal successions do not trigger it |
| State Atheism | **May tear down the country's own shrines** |
| Where modifiers live | **National effects on the JE; local effects on the state** (the engine gives no other home for a state-level key, see Engine facts) |
| Game rule | `grand_monuments_rule`: **Enabled / Disabled.** Disabled makes the building unbuildable and stops everything else |
| JE activation | **Only while the country owns a Grand Monument** |

## Engine facts this rests on

Checked against the engine docs, vanilla script and the mod's own notes:

- **Buildings hold no variables** (`scripting_best_practices.md` § "Buildings Have No Variables", confirmed from the
  owner's `error.log`). One Grand Monument per state, so every per-monument record lives on the **state**.
- **No effect removes building levels.** A smaller building is `remove_building` then `create_building` at the lower
  level, and `create_building`'s `level` takes only a literal; the mod builds at a variable level through the
  `te_construction_market_build_specified_level` ladder (`te_construction_market_build_effects.txt`, levels 1–100).
  The rebuilt building starts on the engine's choice of PMs and lays off its staff. `nuclear_strike_halve_building`
  (`extra_effects.txt`) is the working precedent.
- **The dedication ratchet** (self-referencing `unlocking_production_methods`) is the only per-building PM lock
  (`scripting_best_practices.md` § "Locking Production Methods"). Whether `activate_production_method` overrides it is
  unverified, so this design never switches a dedicated monument's PM from script: rededication rebuilds.
- **Modifiers flow down only** (power bloc → country → state). A state-level key (`state_*`,
  `building_<type>_throughput_add`) in a modifier a building holds reaches nothing. Local effects must be state
  modifiers.
- **JE-scoped modifiers apply to the country** and display in the JE's modifier panel:
  `je:je_grand_monuments ?= { add_modifier = { name = X multiplier = … } }`. The `?=` guards the months before the
  entry is active (`scripting_best_practices.md` § "Journal Entry Modifier Scoping"). A country-scope `has_modifier`
  does not see them.
- **`multiplier = var:…` resolves against ROOT** and re-evaluates on later ticks, so a backing variable must persist
  (never `remove_variable` after the call). State modifiers are refreshed from `on_monthly_pulse_state` (ROOT = the
  state), country and JE ones from `on_monthly_pulse_country`; one refresh site per modifier (CLAUDE.md, dynamic-modifier
  pattern).
- **On-actions:** `on_building_built` (ROOT = the building; the current ceremony shows it fires per level, since its
  re-ask guard exists for that), `on_state_owner_change` (ROOT = the state; no previous-owner scope is documented),
  `on_law_activated`, `on_new_ruler` (ROOT = the character), `on_civil_war_won` (ROOT = the winner, after
  `on_revolution_end`). There is no on-action for a change of state religion; the monthly pulse catches it.
- **Civil-war bookkeeping exists:** `te_cw_role` (1 original, 2 rebel) sits on both sides from the outbreak
  (`te_civil_war_effects.txt`).
- **Triggers and modifiers used here all exist:** `in_default`, `has_famine` (country/state),
  `banking_cycle_is_recession` (mod), `is_revolutionary`, `country_legitimacy_base_add`, `country_prestige_add`,
  `country_authority_add`, `interest_group_ig_<ig>_approval_add` for all eight vanilla IGs,
  `add_radicals_in_state`, `add_treasury`.
- **Loc can render script values** (`[SCOPE.GetRootScope.ScriptValue('x')]`, hundreds of uses in the mod), so tooltips
  read the per-step values instead of repeating them by hand.
- **Precedent for the JE's lifecycle:** `je_strategic_reserve` (`possible` = owns a Hub, `invalid` = owns none,
  `on_invalid` cleans up).

Unverified, in the in-game checklist (§10): the ratchet holding; `on_building_built` firing for a script-created
building; state variables surviving `on_state_owner_change`, and that on-action firing for every kind of transfer
(conquest, cession, release, annexation); telling a civil-war transfer from a conquest; a building readout showing a
multiplied value (shared with #500's checklist).

## 1. Dedications: what a monument says

Every dedication has a **kind**, which decides what can make it fall:

- **regime** — honours a form of government; gives legitimacy while it fits.
- **ruler** — honours one character; gives legitimacy while it fits.
- **faith** — honours the state religion.
- **timeless** — always fits; never contested.

"Fits" is read **live** every month from the owner's current laws, religion and ruler. Only two dedications store a
record on the state: To the Leader (`mon_honoree`, the character) and the Grand Shrine (`mon_faith`, the religion).

| Dedication (PM) | Kind | Fits while | Commission gate | IGs approve / oppose | Local effect (state) | National specific effect |
|---|---|---|---|---|---|---|
| To the Crown (`pm_monument_crown`) | regime | `monument_government_is_crowned` | same | Landowners / Intelligentsia | loyalists from movements | legitimacy |
| To the Republic (`pm_monument_republic`) | regime | `monument_government_is_republican` | same | Intelligentsia / Landowners | loyalists from movements | legitimacy |
| To the Revolution (`pm_monument_revolution`) | regime | Single-Party State or Council Republic | same | Trade Unions / Industrialists | loyalists from movements | legitimacy |
| To the Leader (`pm_monument_leader`) | ruler | `ruler = var:mon_honoree` | Autocracy or Single-Party State, and not crowned | ruler's own IG / strongest IG outside government | loyalists from movements | legitimacy, authority |
| Grand Shrine (`pm_monument_religious`) | faith | `religion = var:mon_faith` and no State Atheism | no State Atheism | Devout / — | **conversion** (see below) | Devout attraction |
| To the Nation (`pm_monument_civic`) | timeless | always | — | Petty Bourgeoisie / — | loyalists from movements | — |
| War Memorial (`pm_monument_war_memorial`) | timeless | always | — | Armed Forces / — | conscription rate | less war support lost to casualties |
| Grand Opera House (`pm_monument_artistic`) | timeless | always | `romanticism` | Intelligentsia / — | Creative Industries throughput | Intelligentsia attraction |
| Botanical Gardens (`pm_monument_naturalist`) | timeless | always | `romanticism` | Rural Folk / — | less pollution | — |
| Grand Observatory (`pm_monument_scientific`) | timeless | always | `empiricism` | Intelligentsia / — | literacy growth | innovation cap |
| Great Exhibition Hall (`pm_monument_industrial`) | timeless | always | `marketing_research`, no Industry Banned | Industrialists / — | migration pull | Industrialists attraction |
| Grand Stadium (`pm_monument_athletic`) | timeless | always | `television_broadcasting` | Trade Unions / — | lower turmoil effects | — |
| Undedicated (`pm_monument_undedicated`) | — | — | — | — | — | — |

"Legitimacy" in the last column comes through the regime total (§2.4), not a per-dedication modifier. Every
dedication also gives **prestige** and **Tourism Industry throughput** (§2). Timeless dedications have no
opponents on purpose: they are the safe choice, the regime ones are divisive, and that is what pays for their
legitimacy.

**The Shrine's local effect is conversion** (today's `state_conversion_mult`), which acts on the state's religious
minorities. It is kept visible here for review; a swap (e.g. to loyalists or to Devout-only effects) is a one-line
change in the registry.

**Identity skins.** The builder's own faith and heritage change wording and art, never effects:
- option wording partitioned by trigger, as the civic dedication's three skins already are
  (`monument_triggers.txt`), e.g. the Shrine as a cathedral, mosque, temple or the Temple for Judaism, and To the Crown
  as a Hall of Dynasties for a Chinese monarchy;
- art by religion, as `monument_events.4` already does. Every reused picture is viewed first (contact sheet), per the
  event-art rule.

**Conquest.** A regime or ruler monument in a conquered state honours a foreign order: it becomes contested for the new
owner (§4). **A conquered shrine is never contested**: it becomes heritage at once, with no Tear Down or Rededicate
offered, because pulling down a conquered people's place of worship is the targeting line.

**A building-panel pick that fails its gate** (a republic choosing To the Crown) is a monument that does not fit. The
contested rule handles it; nothing is special-cased.

## 2. Grandeur and the national totals

### 2.1 Grandeur

A monument's **grandeur is its level.** Levels stay uncapped, and every level adds its share of the local effects and
of the national totals, so a rich country can still pour spare construction into a monument.

### 2.2 The doubling curve

Every effect a monument gives, local and national, follows one curve. The effect grows in **steps of equal size**, and
each step costs **twice the grandeur of the one before**. Inside a step the value grows linearly, so no level is
wasted; at each step the slope halves.

With a first step of *f* grandeur, step *n* completes at *f*·(2ⁿ − 1), and the value at grandeur *G* is about
*step value* × log₂(1 + *G*/*f*). The chain has **8 steps**, after which it is flat:

| Steps complete | Grandeur (*f* = 5) | Construction at 10k/level | That step alone |
|---|---|---|---|
| 1 | 5 | 50k | 5 levels |
| 2 | 15 | 150k | 10 |
| 3 | 35 | 350k | 20 |
| 4 | 75 | 750k | 40 |
| 5 | 155 | 1.55M | 80 |
| 8 | 1,275 | 12.75M | 640 |

By the end each level buys 1/128 of what the first five did, so the flat end is out of reach in practice. Larger *f*
(national totals summed across monuments) move the end proportionally.

**Implementation.** One script value per first-step size (`mon_curve_steps_f5`, `mon_curve_steps_f10`) reads the
grandeur from a variable the caller sets on the scope (`var:mon_curve_in`) and returns the fractional step count: a sum
of eight terms, each `(G − start_k) / size_k` clamped to [0, 1]. **Per-step values live in script values**
(`mon_step_prestige`, `mon_step_legitimacy`, …); the static modifiers carry unit values, and the multiplier variable
is steps × per-step value. The JE and the ceremony tooltips read the same script values, so "next full step at 35
grandeur (you have 28)" and every number in a tooltip are computed, not written.

### 2.3 Which monuments count toward what

| Status | Standing grandeur (prestige, cultural pull) | Regime grandeur (legitimacy) | Per-dedication (specific effect) | Per-IG approval | Local effect | Tourism throughput |
|---|---|---|---|---|---|---|
| **Fits** | yes | yes (regime and ruler only) | yes | yes | yes | yes |
| **Undedicated** | yes | — | — | — | — | yes |
| **Heritage** | yes | — | — | only the Preserve entry (§4.3) | yes | yes |
| **Contested** | — | — | — | only the standing penalty (§4.2) | yes | yes |

The registry test pins this table.

### 2.4 National totals: modifiers on the JE

Each month the country pulse sums grandeur by status (§2.3) and applies, on `je:je_grand_monuments`, one modifier per
total with `multiplier = var:…` from the curve:

| Total | Counts | Modifier (unit values; the multiplier carries step count × per-step value) |
|---|---|---|
| Standing | every Fits, Undedicated or Heritage monument | `mon_national_prestige` (`country_prestige_add`) |
| Regime | Fits monuments of kind regime or ruler | `mon_national_legitimacy` (`country_legitimacy_base_add`) |
| Per dedication | that dedication's Fits monuments | `mon_national_<dedication>` for the five with a specific effect, plus Leader's authority |
| Per IG | signed: + each Fits dedication the IG approves, − each it opposes, plus the §4 ledgers | `mon_ig_approval_<ig>` (`interest_group_ig_<ig>_approval_add`), one per vanilla IG, on the absolute value with the sign applied |

Cultural pull stays a script value (`cultural_pull_from_grand_monuments`), now read from standing grandeur through the
curve instead of `levels / 20`. Its 5-step chain keeps the existing +5 ceiling.

**One cap per IG, across all monuments.** Republic, Opera and Observatory all please the Intelligentsia; their sum
goes through one curve. Monuments can never buy an interest group outright.

### 2.5 Local effects: modifiers on the state

The state pulse (`on_monthly_pulse_state`) runs the curve over the monument's own level and sets two variables on the
state, `var:mon_local_tourism_mult` and `var:mon_local_effect_mult` (steps × each per-step value), then refreshes two
state modifiers from them: `mon_local_tourism` (`building_tourism_industry_throughput_add`) and
`mon_local_<dedication>` (the dedication's local effect). There is one named modifier per dedication even where the
effect is shared (the five loyalist dedications each have their own `mon_local_crown`, `mon_local_republic`, …), so
the state's list names the monument's message; a state holds exactly one of them, since it holds one monument. Each is
named after the monument ("Grand Monument: To the Crown") in the state's modifier list. A building readout of grandeur
and next step, on the Settlement Authority's pattern, is added **only if** #500's check shows building readouts render
a multiplied value.

### 2.6 Wide and tall

Twenty level-1 monuments and one level-20 monument give the same national totals and cost the same construction.
Wide spreads the local effects (each on its own curve, so each state's first levels are its best) and pays twenty
caretaker staffs; tall concentrates them. Nothing rewards a level-1 monument in every state any more, and past the
steepest steps a level buys mostly local effect.

### 2.7 Production methods

The dedication PMs carry only the caretaker staff (`unscaled` employment, as now); maintenance stays in
`pmg_maintenance`. **No PM carries `country_modifiers`, `state_modifiers` or a goods
output** (the registry test pins it). The building panel therefore shows the dedication's name and staff only; the
ceremony tooltips and the JE carry the effects.

## 3. Dedicating, the lock and records

- **Building** is the normal construction queue. **The ceremony** (`monument_events.2`, a `state_event` placed on the
  monument's state) fires when a level of an undedicated monument finishes, as now. It offers the dedications whose
  commission gate the owner meets, each option's tooltip rendering the per-step values from the script values (the
  TOOLTIP MIRROR header and its hand-kept numbers go). **Undedicated** stays an option; the ceremony asks again at the
  next level.
- **Records:** choosing To the Leader sets `mon_honoree` = the ruler on the state; choosing the Shrine sets
  `mon_faith` = the owner's religion.
- **The lock** stays the self-reference ratchet, so the panel shows one row.
- **Records on first sight.** A dedicated Leader or Shrine monument the pulse finds without its record, and without
  the state flag `mon_seen`, gets its record from the current ruler or faith and the flag. This covers panel picks
  and pre-rework saves. After that, **a missing record reads as "does not fit"**, never as "fits".
- **Rededication rebuilds** (§4.3): `remove_building`, then the level ladder at the new level, then the ceremony fired
  directly, since a script-created building may not fire `on_building_built`. The shared ladder
  (`te_construction_market_build_specified_level`, also called by the construction market and tactical-strike
  damage) is **extended** from 100 to 200 cases in place, not copied, so rededication halves any monument up to
  level 400 exactly; above that it rebuilds at 200 and the tooltip says so.

## 4. Contested monuments

### 4.1 When a monument becomes contested

Each month the country pulse re-reads "fits" for every regime, ruler and faith monument; `on_law_activated`,
`on_new_ruler` and `on_state_owner_change` re-read at once. A monument that stops fitting, and is neither contested nor
heritage, becomes **contested**: the state gets `mon_contested`, plus two IG records taken at that moment,
`mon_base_ig` (the new order's base: the IG that **opposed** the old message; for a Leader monument, the strongest IG
outside government at the time) and `mon_supporter_ig` (the IG that **approved** it; for a Leader monument, the old
ruler's IG). While a Leader monument fits, both its IGs are re-read every month; the month it is contested, that
reading is frozen into the two records and no longer follows the government.

**Conquest:** `on_state_owner_change` marks the state's regime and ruler monument contested and turns a shrine into
heritage at once. It does not rely on records surviving the transfer.

**Civil wars are not conquest.** When the new owner carries `te_cw_role` or `is_revolutionary`, or a civil-war ending is
pending (`te_cw_ending_*` globals), `on_state_owner_change` does nothing; the monthly fit test catches the winner's
laws. How reliably this separates the cases is an in-game check.

### 4.2 While contested

- It counts only toward local effects and tourism (§2.3). Its prestige, legitimacy, specific effect and IG approval stop.
- **Standing penalty:** its grandeur counts **negative toward `mon_base_ig`** in the per-IG total, every month it
  stands undecided. Ignoring the question is never free, but there is no deadline. The per-IG curve bounds it.

### 4.3 The three choices

Buttons on the monument's JE row, each with a tooltip spelling out what it does:

| Choice | What happens | Gains | Costs |
|---|---|---|---|
| **Tear Down** | `remove_building`; clears the state's records | its grandeur added to the **teardown ledger** (legitimacy for the new order) and positive to `mon_base_ig`'s ledger | all its grandeur; its grandeur negative to `mon_supporter_ig`'s ledger |
| **Rededicate** | rebuilt at half its level (rounded up), then the ceremony under current laws | half its grandeur, the new message counting in full | treasury, scaled by its level; half its grandeur negative to `mon_supporter_ig`'s ledger |
| **Preserve as Heritage** | stays as it is; `mon_contested` → `mon_heritage` | prestige back, local effects and tourism kept | its grandeur negative to `mon_base_ig`'s ledger |

**No stacking, anywhere.** Every reward and cost of these choices goes into a **ledger**, a country variable that
decays each month, and the ledger feeds its effect through the same curve:

- `mon_teardown_ledger` → `mon_national_teardown` (legitimacy, "The Old Order Torn Down") on the JE; decays ×0.96 a
  month (half in about 17 months, under 10% after five years).
- `mon_ig_ledger_<ig>`, one per vanilla IG, added into that IG's per-IG total (§2.4); decays ×0.97 a month (half in
  about two years, under 10% after six).

So forty level-1 statues torn down in one day give exactly what one level-40 statue gives: the same curve value, once.

### 4.4 Restoration

If a contested or heritage monument's message fits again (the monarchy returns), `mon_contested`/`mon_heritage` lift
and it counts in full. Tear Down is the only permanent choice.

### 4.5 Many at once

When a single fall contests several monuments at once (a revolution, a peace deal), one notification event names them
and offers **Tear them all down / Preserve them all / Decide each in turn**. The rows' buttons stay for the last case.
Conquest and the fall of a Leader each give one event per country per month, listing every monument the change hit.

### 4.6 The AI

Within a few months of a contest, weighted:
- **Tear Down** up under a revolutionary or newly radical government, or when `mon_supporter_ig` is weak or in
  opposition.
- **Preserve** up when the monument is tall (its tourism and prestige are worth keeping).
- **Rededicate** up when the treasury can pay without going negative.

## 5. Vanity backlash

**Hard times** (`monument_hard_times`, country scope): `in_default`, a country-wide `has_famine`, or
`banking_cycle_is_recession`.

When a monument level finishes (`on_building_built`) in hard times:
- **In that state:** `add_radicals_in_state` on a share of its pops.
- **Nationally:** +1 to `mon_vanity_ledger`, which decays ×0.92 a month; the JE modifier `mon_national_vanity` takes
  legitimacy **linearly** from it. A cost is not put on the curve, since a curved cost would make building more in hard
  times cheaper per level.

**Warning first:** whenever hard times hold, the JE shows a red line ("Finishing monument levels now will cause
backlash"), so the cost is never a surprise and the queue can be paused. The notification when backlash lands is a
toast, not an event.

## 6. The Monuments journal entry

`je_grand_monuments` (`je_group_internal_affairs`), on the Strategic Reserve's lifecycle: `possible` = owns a Grand
Monument, `invalid` = owns none, `on_invalid` removes every `mon_national_*` and `mon_ig_approval_*` modifier. It comes
back when a new monument is built. Its `immediate` writes nothing a revolution's winner would lose
(`je_immediate_reset_audit`).

Layout, top to bottom:

1. **National effects:** one line per total with its current value and next step: "Legitimacy +6 · next step at 35
   grandeur (28)". Prestige, legitimacy, each specific effect in force, net approval per IG, and any teardown or vanity
   ledger in force. The JE's modifier panel carries the modifiers themselves.
2. **Hard-times warning** (§5), only while it holds.
3. **One row per monument:** state, dedication (in its skin), grandeur, status (Fits / Undedicated / Heritage /
   Contested). A contested row carries the three buttons, which pass the state through a scripted-GUI datacontext on the
   row (the covert-operations rows' pattern, `gui_modding_guide.md`).

The eight flavour events (`.3`–`.10`) keep firing as now, keyed to dedications and `level >= 3`, and are unchanged
apart from the renamed civic event.

## 7. Game rule and AI

- **Game rule** `grand_monuments_rule` in `extra_game_rules.txt`: *Enabled* (default) / *Disabled*. Disabled fails the
  building's `possible` (with a tooltip) and stops the pulses, the ceremony and the JE. Every check is written as
  `NOT = { has_game_rule = grand_monuments_disabled }`, so a save started before the rule stays enabled. History places
  no Grand Monuments.
- **Building `ai_value`:** today's terms (great or major power +25; a Tourism Industry in the state +50; at war −100),
  plus hard times −100 and a bonus when legitimacy is low.
- **Ceremony `ai_chance`:** a regime dedication when legitimacy is low; To the Leader under Autocracy or a Single-Party
  State; the Shrine when the Devout are in government; otherwise the timeless ones, weighted as now.
- **Contested:** §4.6.

## 8. Replacing the old system

- **PMs:** strip every effect block except employment (§2.7). Add `pm_monument_crown`, `pm_monument_republic`,
  `pm_monument_revolution` and `pm_monument_leader` to the ratchet. `pm_monument_civic` keeps its key and becomes **To
  the Nation**, so old civic monuments stay valid with no migration.
- **Old saves:** old Shrines get `mon_faith` on first sight (§3). The unscaled national effects vanish with the PM
  blocks, which removes the exploit from existing saves too.
- **Ceremony:** the three civic skins become To the Crown / To the Republic / To the Nation options; To the Revolution,
  To the Leader and the identity skins are new options.
- **Loc:** PM names and descriptions, ceremony options and tooltips, JE, buttons, events, modifiers and the concept
  `concept_grandeur`; run `organize_loc.py` (new `mon_` prefix needs a `startswith` rule if any key family has four
  tokens).
- **Remove** the TOOLTIP MIRROR header and the hand-kept numbers in `monument_events.2.*.tt`.

## 9. Numbers — first estimates, calibrated in the plan

| Quantity | First step *f* (grandeur) | Per step | Anchor |
|---|---|---|---|
| Tourism Industry throughput (local) | 5 | +25% | a vanilla monument is +25% (`tourism_throughput_from_monuments`); owner's +5%/level |
| Prestige (standing) | 5 | +25 | each vanilla monument +25 |
| Cultural pull (standing) | 10 | +1, 5-step chain | keeps today's +5 ceiling |
| Legitimacy (regime) | 10 | +2 | vanilla grants are mostly ±5 / ±10 |
| IG approval (per IG) | 5 | ±1 | about ±3 at 35 grandeur and ±5 at 155; vanilla law-change approval 5 / 10 / 20 |
| Leader authority | 5 | +25 | vanilla grants 50–200 |
| Innovation cap (Observatory) | 5 | +3 | today +2 a monument |
| War support lost to casualties (Memorial) | 5 | −3% | today −1% a monument |
| IG attraction (Shrine, Opera, Exhibition) | 5 | +5% | today +2% a monument |
| Local effects | 5 | today's per-level value × 5: loyalists +10%, conversion +10%, conscription +0.05, Creative Industries +10%, pollution −5,000, literacy +0.00025, migration pull +10%, turmoil effects −10% | vanilla `state_conscription_rate_add` grants run 0.05–0.4 |
| Teardown ledger → legitimacy | 5 | +3 | decays ×0.96/month |
| IG ledgers | — | added to the per-IG total | decay ×0.97/month |
| Rededication cost | — | treasury, level × 5,000 | calibrate against a level's construction good at market price |
| Vanity: radicals in the state | — | 5% of its pops per level | — |
| Vanity: legitimacy | — | −3 per unit of `mon_vanity_ledger` | decays ×0.92/month |
| Construction per level | unchanged | 10,000 | — |

The first-step sizes and per-step values are first estimates, checked in play with the debug event.

## 10. Tests, docs, in-game checks

- **`test_grand_monument_registry.py`:** one `DEDICATIONS` table pinning, per dedication, its PM (in the group and the
  ratchet), kind, fit and commission triggers, IG alignment, local and national modifiers (registered types where
  needed), ceremony option and skins, JE text, AI weight and loc. Plus: no dedication PM carries `country_modifiers`,
  `state_modifiers` or a goods output; the §2.3 table, as the status conditions in each total's script value; the
curve's eight terms. It is the add-a-dedication checklist,
  like `test_resettlement_programme_registry.py`.
- **Debug:** `te_debug_monuments` in `events/te_debug_*` (set a monument's level, force a contest, force hard times,
  print totals) and `TE_MONUMENTS:` lines in `debug.log` for each month's totals and ledgers.
- **CI:** the `--strict` audits (`event_image`, `silent_variable`, `event_context`, `modifier_multiplier_var`,
  `loc_render`, `je_immediate_reset`, `empty_effect`) cover the new events, buttons and modifiers.
- **Docs:** rewrite `mod_systems.md` § "Grand Monuments"; the player guide's `02-timeline.md` § Grand monuments (and
  line 159, which lists the Grand Monument as a Tourism producer), `10-influence.md` (cultural pull), `07-states.md`
  (the "+1% per level" throughput line) and `16-reference.md`, then rebuild the PDF. Lessons into
  `scripting_best_practices.md`.
- **In-game checklist** (the PR body), including the engine questions:
  1. The ratchet holds: a dedicated monument's panel shows one row.
  2. `on_building_built` fires per level, and whether it fires for a script-created (rebuilt) monument.
  3. State variables survive `on_state_owner_change`; the on-action fires for conquest, cession, release and
     annexation.
  4. A civil-war transfer is told apart from a conquest (§4.1).
  5. The rebuild at half level keeps the new dedication, rehires and reads the right level.
  6. JE-scoped IG approval modifiers show in the IG's approval tooltip.
  7. The JE's "next step" lines and the ceremony tooltips show real numbers.
  8. A building readout, if added, shows the multiplied value.
  9. Contest on a revolution: Crown monuments contested, bulk event offered, Preserve / Tear Down / Rededicate each do
     what their tooltips say; restoration lifts the flags.
  10. A Leader monument contests on the ruler's death; the strongest-opposition IG reads correctly.
  11. Vanity backlash lands only in hard times, with the warning line shown beforehand.
  12. The rule's Disabled setting: no building, no JE.

## Out of scope (possible extensions)

- A monument as a target for rivals: a covert defacement operation, prestige lost when its state is occupied.
- Superlinear upkeep for colossal monuments.
- A state-panel tile for the monument.
- Recurring decision events tied to a monument (anniversaries that ask something), beyond the eight flavour events.
- A dedication for a war won (a triumphal arch keyed to a recent victory).
- Flavour events for the four new regime and ruler dedications (the existing eight stay).
- Wonders (`bg_monuments`) and megaprojects joining the legacy mechanic.
