# Combat Unit Balance Review

## Scope and method

Scope: 25 mod-side combat units in
`common/combat_unit_types/extra_combat_units.txt`, spanning eras 5
(mobile_armor inheritor) through 11 (Grey Goo / DEW Tank /
bioenhanced marines / orbital antimatter strikes).

Method: a one-off auditor (`scripts/analysis/combat_unit_balance_audit.py`)
extracts per-unit:

- `unit_offense_add` + `unit_defense_add` from the `battle_modifier` block (= "power")
- `max_manpower` (battalion size — drops sharply for elite units)
- Total upkeep cost from the auto-generated cost comment
- Unlocking tech (mapped to era via a curated lookup)
- Power-per-1k-cost ratio: rough "how much combat power do you get per money spent on upkeep"

**Caveats baked in:**

1. The audit's "power" is just `offense + defense`. Real Vic3 combat
   weights these unequally based on whether the formation is attacking
   or defending; it ignores morale loss, devastation, kill rate, etc.
   The metric is a coarse first-pass.
2. The audit normalizes cost by per-1000-men, but **mod design uses
   `max_manpower` as a balance lever**. Elite units (Grey Goo, orbital
   bombardment, swarm bots) deliberately have very low manpower
   (10–25), which inflates per-1000-man cost dramatically — these
   units are *meant* to be one-or-two-per-formation specialists.
   So a low ptc on a 10-man unit is intentional, not a bug.
3. Era mapping is now read directly from the tech files
   (`build_tech_era_map()` walks `common/technology/technologies/` plus
   the vanilla `game/common/technology/technologies/` tree and pulls
   each tech's `era = era_X` field). The previous hand-curated dict had
   drifted: four units (`jet_powered_fighters`, `stealth_aircraft`,
   `orbital_weapons_platforms`, `stealth_marines`) fell through entirely,
   and the dict had `swarm_technology` / `space_militarization` /
   `augmented_reality_warfare` at era_10 when their tech files actually
   place them in era_11. Several units' inline `# era N` comments are
   also now known to lag the tech-file truth — trust the audit, not the
   comment.

**Mod design philosophy reminder (from user):** combat units should
get *much better* with tech AND *much more expensive*. Power-to-cost
ratio should stay roughly constant or favor cost-cutting at lower tech
(low-tier units stay cost-effective in mass).

---

## Themes

### Theme 1: Tank chain is exemplary balance

`combat_unit_group_tanks` maintains a **perfectly flat power-per-cost
ratio of 0.04** across eras 7, 8, 10, and 12:

| Unit | Era | Power | ptc |
|---|---|---|---|
| `combat_unit_type_main_battle_tank` | 7 | 400 | 0.04 |
| `combat_unit_type_reactive_armor_tank` | 8 | 640 | 0.04 |
| `combat_unit_type_railgun_tank` | 10 | 2000 | 0.04 |
| `combat_unit_type_DEW_tank` | 12 | 4000 | 0.04 |

Power doubles every two eras; cost doubles in lockstep. This is the
**reference standard** the mod's design philosophy describes —
units get much better and much more expensive in lockstep.

### Theme 2: Cavalry chain is also flat at 0.04

`combat_unit_group_cavalry` (light_scout_tanks → stealth_reconnaissance
→ holographic_ambush) holds 0.04 ptc across eras 7 / 9 / 11.

These two groups (tanks + cavalry) are the design baseline.

### Theme 3: Infantry chain power-cost ratio collapses 13× to 0×

| Unit | Era | Power | mp | cost/1k men | ptc |
|---|---|---|---|---|---|
| `combat_unit_type_armored_infantry` | 6 | 160 | 1000 | 1,200 | 0.13 |
| `combat_unit_type_robotic_soldiers` | 10 | 470 | 100 | 62,000 | 0.01 |
| `combat_unit_type_swarm_bots` | 11 | 940 | 25 | 506,400 | 0.00 |
| `combat_unit_type_grey_goo` *(now Utility Fog Phalanx)* | 12 | 1880 | 10 | 2,490,000 | 0.00 |

Two interpretations:

- **Intended:** late-tier infantry are elite specialists. Max manpower
  (1000 → 100 → 25 → 10) drops because each "battalion" is a single
  exotic unit. Per-1000-men cost should not be the metric — per-unit
  power should be.
- **Concerning:** even on a per-unit basis, the cost ramp is steep.
  Grey Goo's per-unit upkeep is **24,900** per individual — a single
  Grey Goo battalion of 10 costs ~250k upkeep, vs. an armored infantry
  battalion of 1000 men at ~1,200 total upkeep.

**Open question (T3):** is the elite-specialist interpretation correct?
That is, is the mod's design philosophy "tanks scale flat; infantry
becomes elite-specialist"? That's a coherent design but it deviates
from what I'd assume from the user's stated philosophy ("scaling
proportionally"). It might be better to call out two design
philosophies — flat-ptc for tanks/cavalry and elite-specialist for
infantry/artillery — rather than treating it as one rule.

### Theme 4: Artillery chain has the same elite-specialist drop

| Unit | Era | Power | mp | ptc |
|---|---|---|---|---|
| `combat_unit_type_motorized_artillery` | 6 | 200 | 1000 | 0.10 |
| `combat_unit_type_guided_artillery_projectiles` | 7 | 300 | 1000 | 0.07 |
| `combat_unit_type_networked_guided_artillery_projectiles` | 9 | 660 | 500 | 0.03 |
| `combat_unit_type_orbital_bombardment` | 11 | 1320 | 10 | 0.00 |
| `combat_unit_type_orbital_precision_antimatter_strikes` | 12 | 2640 | 10 | 0.00 |

Same pattern: progressive elite-specialization. Orbital bombardment
and antimatter strikes are functionally a different category from
field artillery.

### Theme 5: Marines drop more gradually

| Unit | Era | Power | mp | ptc |
|---|---|---|---|---|
| `combat_unit_type_combined_arms_marines` | 6 | 120 | 1000 | 0.13 |
| `combat_unit_type_stealth_marines` | 8 | 280 | 500 | 0.08 |
| `combat_unit_type_networked_marines` | 10 | 350 | 500 | 0.04 |
| `combat_unit_type_bioenhanced_marines` | 11 | 705 | 200 | 0.02 |

Marines elite-specialize less aggressively than infantry. The drop
from 0.13 to 0.02 across 5 eras is meaningful but not extreme. With
era assignments now resolved, the chain shows a clean monotonic ptc
decay (0.13 → 0.08 → 0.04 → 0.02) rather than an out-of-order
`stealth_marines = ?` outlier.

### Theme 6: Aircraft chain holds 0.01 ptc across all eras

With era resolution now reading directly from the tech files, all
five aircraft are filed:

| Unit | Era | Power | mp | ptc |
|---|---|---|---|---|
| `combat_unit_type_bomber_aircraft` | 6 | 500 | 200 | 0.01 |
| `combat_unit_type_jet_powered_fighters` | 7 | 750 | 200 | 0.01 |
| `combat_unit_type_stealth_aircraft` | 8 | 1150 | 200 | 0.01 |
| `combat_unit_type_orbital_tactical_vehicles` | 11 | 2300 | 100 | 0.00 |
| `combat_unit_type_orbital_weapons_platforms` | 12 | 4600 | 10 | 0.00 |

Era 6–8 conventional aircraft hold a flat 0.01 ptc — internally
consistent with each other, but an order of magnitude below the
0.04–0.13 ground-unit baseline. See T3.

The two orbital aircraft drop into the elite-specialist regime —
`orbital_weapons_platforms` is the highest single-unit power in the
dataset (4600) at the lowest manpower (10), giving it the highest
per-unit cost (~14M per individual). Functionally a different category
from atmospheric aircraft.

### Theme 7: Era 6 ptc range is 0.10–0.13 (relatively tight)

Within era 6, all four units sit at 0.10–0.13 ptc — a tight cluster.
This is good — it means the early-mod baseline is internally
consistent. The divergence opens up in mid-game (era 7+).

---

## Per-group power progression table

```
combat_unit_group_tanks
  era_7  main_battle_tank          pwr= 400  ptc=0.04
  era_8  reactive_armor_tank       pwr= 640  ptc=0.04
  era_10 railgun_tank              pwr=2000  ptc=0.04
  era_12 DEW_tank                  pwr=4000  ptc=0.04

combat_unit_group_cavalry
  era_7  light_scout_tanks         pwr= 300  ptc=0.04
  era_9  stealth_reconnaissance    pwr= 640  ptc=0.04
  era_11 holographic_ambush        pwr=1280  ptc=0.04

combat_unit_group_infantry
  era_6  armored_infantry          pwr= 160  ptc=0.13
  era_10 robotic_soldiers          pwr= 470  ptc=0.01
  era_11 swarm_bots                pwr= 940  ptc=0.00
  era_12 grey_goo (Utility Fog)    pwr=1880  ptc=0.00

combat_unit_group_artillery
  era_6  motorized_artillery       pwr= 200  ptc=0.10
  era_7  guided_artillery          pwr= 300  ptc=0.07
  era_9  networked_guided_artil    pwr= 660  ptc=0.03
  era_11 orbital_bombardment       pwr=1320  ptc=0.00
  era_12 orbital_antimatter        pwr=2640  ptc=0.00

combat_unit_group_marines
  era_6  combined_arms_marines     pwr= 120  ptc=0.13
  era_8  stealth_marines           pwr= 280  ptc=0.08
  era_10 networked_marines         pwr= 350  ptc=0.04
  era_11 bioenhanced_marines       pwr= 705  ptc=0.02

combat_unit_group_aircraft
  era_6  bomber_aircraft           pwr= 500  ptc=0.01
  era_7  jet_powered_fighters      pwr= 750  ptc=0.01
  era_8  stealth_aircraft          pwr=1150  ptc=0.01
  era_11 orbital_tactical_vehicles pwr=2300  ptc=0.00
  era_12 orbital_weapons_platforms pwr=4600  ptc=0.00
```

Refresh by running `.venv/bin/python scripts/analysis/combat_unit_balance_audit.py`.

---

## Open questions for back-and-forth

1. **T1**: Confirm tank/cavalry chains are the intended baseline (flat
   ptc). They're working as the design philosophy describes.
2. **T2**: Is the **infantry/artillery elite-specialist drift** intended?
   That is, do you want late-era infantry/artillery to become
   one-or-two-per-formation specialists (very low max_manpower, very
   high per-unit cost), or should they scale flat like tanks?
3. **T3**: Aircraft units have very low ptc (0.01) even at era 6. Is
   that intentional (aircraft are intrinsically expensive vs ground)
   or is the early bomber undercosted?
4. **T4**: Per-unit cost for orbital units (`orbital_weapons_platforms`,
   `orbital_bombardment`, `orbital_precision_antimatter_strikes`,
   `orbital_tactical_vehicles`) is an order of magnitude above ground
   units. This matches their "small handful per nation" theme but worth
   confirming.
5. **T5 (resolved):** the auditor now reads `era = era_X` directly
   from each tech file rather than relying on a hand-curated dict, so
   newly added techs/units are picked up automatically.
6. **Concrete first edit candidate:** `combat_unit_type_swarm_bots` at
   max_manpower 25 with 506,400/1k cost is striking. Is the 25 number
   deliberate (you fielded it out of the gate as elite-from-start), or
   was 100 or 250 the intent?

---

## Recommended follow-up workflow

1. ~~Fix the `TECH_ERA` lookup gaps and re-run.~~ Done — eras now
   auto-resolve from the tech files.
2. Walk the per-group table and decide for each group: flat-ptc design
   target, or elite-specialist drift. Tanks/cavalry are clearly flat;
   infantry/artillery clearly aren't. Pick the rule per group.
3. For the units that should be flat but aren't (if any), retune
   either max_manpower up or upkeep_modifier down to bring per-unit
   power-to-cost in line.
4. For the elite-specialist units, audit the "few but lethal" balance
   on a per-unit basis: a Grey Goo unit at 24,900 upkeep delivering
   188 power (vs an armored infantry unit at 1.2 upkeep delivering
   0.16 power) — the Grey Goo is **20,750× the cost for 1,175× the
   power**. That's a worse ratio than even elite-specialist intent
   typically wants.

---

## Caveats

- **Per-unit power treatment:** the audit treats `offense + defense`
  as a scalar. Real Vic3 combat weights these by formation role and
  battle stance.
- **No interaction with techs:** units' real power scales with
  research-tree modifiers (e.g. `country_unit_offense_mult` from
  late techs). The raw `unit_offense_add` value isn't the in-battle
  number.
- **No upgrade-chain analysis:** the `upgrades = { ... }` block in
  each unit isn't audited; it determines who replaces whom and is
  worth its own pass.
- **Manpower vs cost:** elite units can be balanced by capping how
  many you can field. The audit doesn't currently surface this lever
  (it's set per-formation in scripted barracks PMs).
