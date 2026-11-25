# Space fleets: positions on a quarter-month clock, and battles settled on contact

Status: design, 2026-11-25, from issue #2065 (the owner's calls of that day). The owner was away when it was written and asked that the issue's open questions be set at reasonable first guesses, to be retuned later; § 3 lists each guess. Part 1 is built in the first PR, part 2 in a second PR on top of it. Full Colonies only.

Builds on the fleets design (`docs/superpowers/archive/specs/2026-10-26-solar-colonization-fleets-design.md`: § 1.2 legs, § 6 orders, § 7 combat, § 14 the AI) and on `docs/systems/mod_systems/space_race.md` § Fleets, Space Command and combat.

## 1. Part 1: fleet positions on a quarter-month clock

### 1.1 Why

A leg takes whole months today, rounded half up with a minimum of one, and fleets land only on the 1st. In the late game every inner trip takes one month, so a nearby fleet gets there no sooner than a distant one, and the landing month is set by the month of the order rather than its day: a one-month leg ordered on the 25th lands six days later, one ordered on the 2nd takes 29 days. The AI orders on its own 30-day country pulse, which falls on a different day for each country.

### 1.2 The clock

- **Four ticks a month: the 1st, 8th, 15th and 22nd.** Not a true 7-day cadence, which would drift against the monthly launch windows. The gaps are 7, 7, 7 and 7 to 10 days; four make a month.
- **The tick index** is `te_history_month_index × 4 + q`, q = 0 on the 1st, 1 on the 8th, 2 on the 15th, 3 on the 22nd. The engine gives the month but no day of the month a script can rely on (`day_value` is undocumented and unused anywhere), so each tick stores its index in the global variable `sr_fl_tick`, and every reader goes through the script value `sr_fl_tick_now`: the larger of `sr_fl_tick` and `te_history_month_index × 4`. The second term makes a reading on the 1st right before the 1st's tick has run, and keeps the index moving if mid-month ticks stop.
- **The 1st** is the global monthly step (`sr_fl_global_month`, from `sr_sites_global_monthly`). It sets `sr_fl_tick` to the month's quarter 0, then queues the other three.
- **The 8th, 15th and 22nd** are three hidden events, `space_race_events.120`, `.121` and `.122`, queued with `days = 7`, `14` and `21` on one fleet power (the first alive in `sr_fleet_powers`), since the global pulse has no ROOT to queue on. The precedents are `te_pm_retooling_weekly_schedule` and `st_dp_escalation_weekly_schedule` (`common/on_actions/extra_on_actions.txt`). The events take no `trigger` (a delayed event's trigger is read when it is queued and again when due: `scripting_best_practices.md`, "A Delayed `trigger_event` Re-Checks Its Trigger"); `immediate` checks Full Colonies and calls `sr_fl_tick_step = { Q = 1 }` (2, 3).
- **A guard against running a tick twice.** `sr_fl_tick_step` runs only when `sr_fl_tick` is below the index it would set. A save loaded with the events queued, or a second fleet power queued by mistake, then does nothing twice.
- **The clock country dies mid-month.** Its queued events die with it. The 1st lands every fleet whose index has passed, since a landing tests `arrive <= sr_fl_tick_now`, and queues the next month's ticks on a live power.
- **What a tick does** (part 1): land every fleet whose index has come (`sr_fl_each_slot = { DO = arrive }`) and rebuild the location records (`sr_loc_rebuild`). The 1st does the same and then everything it does today. Part 2 adds the battles to every tick.

### 1.3 Legs in quarters

- `gen_launch_windows.py` emits every leg in quarters, `quarters_of(days) = max(1, floor(days ÷ 7.609 + ½))` (a quarter is `MONTH_DAYS ÷ 4`), keeping the minimum of one and the rule that a better drive is never slower. The scripts are renamed with the unit: `sr_leg_quarters_<drive>_<a>_<b>`, `sr_leg_quarters_rapid_<drive>_<a>_<b>`, and per slot `sr_fl_<n>_leg_quarters_<loc>` and the in-flight `sr_fl_<n>_leg_quarters`. The rename makes a missed reader an unknown script value at load, not a silent month read as quarters.
- **Earth's outbound legs** stop reading the colony fleets' transit (`sr_transit_<drive>_<body>`, which stays in months for colony fleets): they get their own quarters by `sr_launch_offset_<body>`, from the same departures and days.
- **Rapid response** keeps its rule on the new unit: one drive ahead; antimatter's own at three quarters of antimatter's quarters, rounded up, at least one.
- The issue's medians (2040–2080), for scale:

| Earth to | Antimatter: days · months now · quarters | Fusion torch: days · months now · quarters |
|---|---|---|
| Mercury and Venus | 18 · 1 · 2 | 32 · 1 · 4 |
| Mars | 22 · 1 · 3 | 39 · 1 · 5 |
| Asteroid Belt | 28 · 1 · 4 | 49 · 2 · 6 |
| Jupiter | 38 · 1 · 5 | 70 · 2 · 9 |
| Saturn | 51 · 2 · 7 | 107 · 4 · 14 |

### 1.4 Orders and landings

- `sr_fl_dispatch` sets `_depart` to `sr_fl_tick_now`, `_leg_quarters` to the leg and `_arrive` to their sum. An order given between ticks counts from the last tick, so it lands up to a quarter early against real days, never late.
- `sr_fl_arrive_at` lands a fleet once `_arrive <= sr_fl_tick_now`.
- **Readers in `gen_space_fleets.py` move to ticks:** the AI's reach test (`leg_quarters <= 24`, six months) and the inbound-first comparison; the attack test (`sr_fl_ai_attack_quarters = 48`, twelve months); `sr_loc_inbound_first_<loc>`; the card's weeks left (`sr_disp_fl_<n>_weeks_left`) and transit fraction; the destination popup's trip; the Locations strip's first landing; the Hostile Fleet cell and the Earth alert's landing (`sr_earth_alert_arrive`, `sr_fl_alert_arrive`); the console's landing (`sr_fl_debug_land_at`).
- **The panel counts the trip in weeks.** A tick is called a week in player text ("lands in 3 weeks"), since the ticks fall a week apart but for the month's last. The player guide's Hostile Fleet cell, fleet card and destination button follow.
- **Old saves.** Fleets shipped in release 1.3.4, so fleets in flight exist in players' saves. Once a save (`sr_fl_ticks_migrated`), on the first 1st after the update and before any landing, every slot in flight has `_depart` and `_arrive` multiplied by 4 and `_leg_months` turned into `_leg_quarters` the same way, and the two alert variables likewise. A fleet then lands on the 1st of the month it would have landed in.

### 1.5 What stays monthly

Space Command's build, upkeep, docking, refuel, repair, refit, supply and attrition; the marines' refill; personnel; modules; colony fleets, shipments and settlers; launch windows (by departure month: a leg's figures are read in the month it leaves); the AI's review and attack planning (its 30-day country pulse); and in part 1 the combat round itself.

### 1.6 Checks

- **`fleet_leg` self-check**, in ticks: OK at the first landing on time (`late < 1`), BROKEN at the first landing four ticks (a month) or more after its index.
- **`fleet_clock` self-check, new**: OK the first time a 22nd's tick runs; BROKEN on a 1st when the previous 1st queued the clock on a country still alive and the 22nd never ran (`sr_fl_tick` short of the previous month's quarter 3). The fallback, should it read BROKEN: tick from every fleet power's own `days = 7/14/21` events instead of one, the guard keeping it once.
- Tests: `test_launch_windows.py` (quarters, never slower, at least one, the exact legs' own tables, rapid response), `test_space_fleets.py` (the clock's wiring, the guard, dispatch and landing on ticks, the readers, the migration) and `test_space_fleet_window.py` (weeks).
- Play-test list (`docs/testing/solar-colonies-playtest.md`): a fleet ordered on the 3rd lands on the tick its weeks say; the card counts down by a week a tick.

## 2. Part 2: battles settled on contact

### 2.1 Why

Combat is a month-long Lanchester round at every location on the 1st (`sr_fleet_k` 0.1 a month), with who fights set by posture; battle and siege share one round (`sr_combat_at`'s step 3 adds the Defences' fire to the fleets' losses); nothing retreats; and the AI's defence sends its strongest free fleet without comparing it to the attacker. Battles that take months fit weapons with no cover poorly: missiles and impactors at kilometers per second, lasers at light speed.

### 2.2 A tick's order

On every tick, the 1st included: landings, the location records, then at each location where two powers at war meet: the AI sets its fleets' Engage / Avoid (§ 2.7); at Earth the ground-to-orbit batteries fire once (§ 2.5); the battle (§§ 2.3, 2.4); the broken fleets leave (§ 2.4); the records (§ 2.8). On the 1st the siege's monthly step follows (§ 2.6). An order changed mid-week takes effect at the next tick, so no button runs combat.

### 2.3 Who fights

A per-fleet setting, **Engage / Avoid** (`sr_fl_<n>_avoid`; absent is Engage, a new fleet's default), separate from posture, decides each pair of fleets at war at a location:

- Both engage: they fight.
- Neither engages: no battle.
- One engages: they fight if the engager's **pace** (`sr_fl_<n>_pace`: its drive, one ahead for rapid response alone) is at least the avoider's, or if the avoider is **tied** there. A fleet is tied when its owner holds a colony at the location (`sr_loc_held_<loc>`), when it closes in (posture 3), interdicts (4), or stands off (2) where there is a hostile world (`sr_fl_<n>_has_hostile_world`, the blockade's case). Earth counts as everyone's colony, so at Earth every fleet is tied and any engager catches any fleet.
- Fleets are compared one by one: a slow fleet can be caught while a faster one of the same nation gets away.
- Posture keeps what it does to colonies (blockade, siege, interdiction) and no longer decides who fights whom.

### 2.4 The battle

- **Settled in one call.** Every fleet in a fighting pair at the location joins. The round repeats in small steps inside a bounded `while` until no fighting pair is left. In each step, each fleet's fire is shared among the hostile fleets it is paired with in proportion to their strength, and each fleet loses `sr_bt_k` (0.05) × its strength × the sum, over the fleets it is paired with, of their fire per point they engage. That is the square law of today's round, per fleet instead of per posture, so allies and three-way wars work as they do now. Losses go on through `sr_fl_take_losses_at` (screens first, half destroyed, half damage). Strength and fire are read again each step. The step size sets how fine-grained the fight is, not how long it takes: an even fight breaks in about 14 steps. A ceiling of 60 steps (`sr_bt_max_steps`) stops a fight of fleets with almost no fire (tenders against tenders); it goes on at the next tick.
- **Each fleet breaks on its own.** A fleet breaks once it has lost `sr_bt_break_share` (0.5) of the strength it brought to this battle, and drops out of it. After the battle it heads for the nearest dock it may depart for (Earth, or a location where its owner holds a Spaceport; nearest by its quarters), through the same `sr_fl_<n>_may_depart_<loc>` an order passes. A fleet already at a dock (Earth, or its own Spaceport) stays there. With no dock in reach it stays where it is, out of this battle, and can be caught again at the next tick. The break share is counted afresh in each battle.
- A fleet below `sr_fl_minimum_strength` drops out as destroyed; the monthly step clears it, as today.
- **The Orbital Battlestation** is in the loop at Earth, for its owner: it always engages, is always tied, never breaks, and fights until its strength is gone. It regains 10% a month as today.

### 2.5 The ground-to-orbit batteries

They stay outside the loop: once a tick, before the battle, each owner's batteries fire on the fleets at Earth of every power at war with it, shared by strength. A tick's losses are `sr_fleet_k × sr_battery_tick_share (0.25) × their fire`, so a month of ticks deals what a month's round deals today. The kinetic part's debris is a quarter of today's a tick, and only when there was a fleet to fire on.

### 2.6 The siege, monthly

The siege stays on the 1st: the Defences' fire on fleets closing in, integrity, seizure, destruction and blockade, with their monthly figures (`sr_fleet_k` 0.1 for the Defences' fire, integrity regained a month, `sr_destroy_months`). It is today's `sr_combat_at` with the fleet-against-fleet losses taken out: the gather by posture stays (closing-in strength and fire on Defences, marines, fire to destroy, the hostile stationed strength that shares a closing-in fleet's fire and bars a seizure, the Orbital Battlestation counting as stationed at Earth), the Defences' losses on closing-in fleets stay, and so do debris at Earth and the worlds' step. The batteries and the battle records leave it. A relief fleet fights the besieger when it lands, either way, through the battle.

### 2.7 The AI

- **Engage or Avoid, each tick at a location with hostile fleets:** it engages when its win test says it would win and avoids otherwise. The test is the square law's: our fleets' strength there × their fire against the same product for the fleets there of every power at war with us, the Orbital Battlestation counted on its owner's side at Earth. It engages when ours is at least theirs (`sr_fl_ai_engage_margin`, 1).
- **`sr_fl_ai_defend` gets the test.** For a threatened location: hostile = the fleets there and on their way; ours = ours there and on our way. Already winning: nothing is sent. Else the strongest free fleet that reaches in time, if it makes ours win; else every free fleet that reaches, if together they win; else none. So the AI holds back or combines fleets instead of feeding them in one at a time. The old gate (send nothing while any fleet of ours is there or bound) gives way to "already winning".
- The attack rule's 1.5× margin stays.

### 2.8 Records against the new cadence

- **`.101`**, the battle report: one per battle, at most one a tick for a country (`sr_battle_notice_pending` for 6 days, where it was 25).
- **`sr_loc_battle_<loc>`** stays a month stamp: the Locations strip reads it as "a battle this month or last".
- **`sr_site_bombard_<key>`** against `sr_destroy_months`: unchanged, as the siege stays monthly.
- **War support's `sr_ws_battle`**: set by each battle for 30 days, as each month's round set it; the later battle's verdict stands.
- **Debris at Earth**: every point lost in a battle there, at today's figures.

### 2.9 The panel and the guide

- An **Engage / Avoid** button among a fleet's orders, on the card and the Fleets window's page, its hover giving the rule of § 2.3. It takes effect at the next tick. Like a posture, it can be changed only with a Space Command; without one a fleet keeps the setting it had.
- The player guide's Battles in space is rewritten: battles on contact, Engage / Avoid, pace and ties, the break and the retreat, the batteries once a week; the posture table keeps what each posture does to colonies.
- The system doc's combat section and the fleets design's § 7 point here.

### 2.10 Checks

- Self-check **`fleet_battle`**: OK at the first battle that ends with a break or a fleet destroyed inside the step ceiling; BROKEN at the first that reaches the ceiling with two fleets each above half their fire still paired (the step size or the ceiling is wrong), with the figures.
- Tests: the battle's wiring (every tick, after the landings and the batteries; the siege only on the 1st), the pair rule, the break, the retreat's gate, the batteries' share, the AI's two tests, the records.
- Play-test list: `event te_debug_space_race.6` option o (the strongest enemy puts a fleet at Earth) and n (fill the reserve), then watch a battle settle within the tick, a break and a retreat, an Avoid that escapes and one that is caught.

## 3. The open questions: first guesses

| Question | First guess | Why |
|---|---|---|
| The break share | 0.5 of the strength a fleet brought to the battle | The issue's "about half"; a 2:1 fight then costs the winner about a tenth |
| The siege on the monthly step or the tick | Monthly | All its figures are monthly (integrity regained, three months to destroy, the Defences' 0.1); moving it would retune them all for little |
| The batteries' fire per tick | A quarter of a month's | A month of ticks deals what a month's round deals today, so their tuning holds |
| A forecast in the destination popup and the alerts | Not in these PRs | The popup already shows the enemy's strength there and on its way; the AI's win test is the figure to show if wanted (a follow-up issue) |
| The step size and ceiling | 0.05 a step, 60 steps | An even fight breaks in about 14 steps, a 4:1 in 3; the ceiling only bites on fleets with almost no fire |
| The AI's engage margin | 1 (win or draw) | "Engages when its win test says it would win" |

## 4. Follow-ups, separate

- Stances in place of Engage / Avoid: Avoid, Hit and run (breaks early), Regular, Fight to the last (never breaks) (issue #2065).
- A battle forecast in the destination popup and the alerts (§ 3).
- #2057 (supply in flight) touches the same transit code; #2053 (the Fleets tab's frame rate) matters now that the card gains a control.
