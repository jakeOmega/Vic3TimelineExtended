# Combat Unit Balance Review

## Scope and method

Scope: 25 mod-side combat units in
`common/combat_unit_types/extra_combat_units.txt`, spanning eras 5
(`mobile_armor` REPLACE on `combat_unit_type_heavy_tank`) through 12
(DEW Tank / Grey Goo / orbital antimatter strikes / orbital weapons platforms).

Method: a one-off auditor (`scripts/analysis/combat_unit_balance_audit.py`)
extracts per-unit:

- `unit_offense_add` + `unit_defense_add` from the `battle_modifier` block
  (= raw `power`)
- `max_manpower` (battalion size — drops sharply for elite units)
- `eff_pwr` = (off+def)/2 × max_manpower/1000 (vanilla's `POWER_PROJECTION`
  formula; the actual per-battalion combat contribution)
- Total upkeep cost from the auto-generated cost comment
- Unlocking tech (mapped to era automatically by walking the tech files)
- `ptc` = `power × manpower / (cost × 1000)` = cost-effectiveness in effective
  combat power per unit upkeep. **NOTE:** previous versions of this doc read
  `ptc` as a per-1000-men metric; that's incorrect. The manpower term is
  already in the numerator, so `ptc` already accounts for `max_manpower`
  changes. Don't double-discount it.

**Why effective power matters:** vanilla `common/script_values/command_values.txt`
selects battalions for battle by `manpower × morale × mobilization × stat`,
and `BATTLE_RAW_MANPOWER_INFLICTED_CASUALTY_RATIO` etc. in
`common/defines/00_defines.txt` exchange casualties proportional to engaged
manpower. So a 200-man unit with offense/defense 100 is roughly **1/5 the
combat strength** of a 1000-man unit at the same stats. `max_manpower` is
multiplicative with offense/defense, not secondary.

The audit's older "raw power" view (offense+defense only) was manpower-blind
and badly misled the previous balance pass: late-tier "elite" infantry,
artillery, aircraft, and marine units sat at `max_manpower = 10–25`, which
collapsed their effective combat power below era-6 baselines despite raw
stats that looked impressive on the unit screen.

---

## Current per-group progression (after 2026-05 retune)

```
combat_unit_group_tanks
  era_7  main_battle_tank          pwr= 400  eff= 200  ptc=0.04
  era_8  reactive_armor_tank       pwr= 640  eff= 320  ptc=0.04
  era_10 railgun_tank              pwr=2000  eff=1000  ptc=0.04
  era_12 DEW_tank                  pwr=3220  eff=1610  ptc=0.04

combat_unit_group_cavalry
  era_7  light_scout_tanks         pwr= 300  eff= 150  ptc=0.04
  era_9  stealth_reconnaissance    pwr= 640  eff= 320  ptc=0.04
  era_11 holographic_ambush        pwr=1280  eff= 640  ptc=0.04

combat_unit_group_infantry
  era_6  armored_infantry          pwr= 120  eff=  60  ptc=0.10
  era_10 robotic_soldiers          pwr= 825  eff= 248  ptc=0.08
  era_11 swarm_bots                pwr=2215  eff= 443  ptc=0.07
  era_12 grey_goo                  pwr=5975  eff= 747  ptc=0.06

combat_unit_group_artillery
  era_6  motorized_artillery       pwr= 170  eff=  85  ptc=0.08
  era_7  guided_artillery          pwr= 325  eff= 162  ptc=0.08
  era_9  networked_guided_artil    pwr= 910  eff= 364  ptc=0.07
  era_11 orbital_bombardment       pwr=2000  eff= 100  ptc=0.01
  era_12 orbital_antimatter        pwr=3200  eff= 160  ptc=0.01

combat_unit_group_marines
  era_6  combined_arms_marines     pwr=  90  eff=  45  ptc=0.10
  era_8  stealth_marines           pwr= 190  eff=  76  ptc=0.08
  era_10 networked_marines         pwr= 615  eff= 184  ptc=0.07
  era_11 bioenhanced_marines       pwr=1170  eff= 292  ptc=0.07

combat_unit_group_aircraft
  era_6  bomber_aircraft           pwr= 840  eff=  84  ptc=0.02
  era_7  jet_powered_fighters      pwr=1480  eff= 148  ptc=0.02
  era_8  stealth_aircraft          pwr=3000  eff= 300  ptc=0.02
  era_11 orbital_tactical_vehicles pwr=7920  eff= 396  ptc=0.01
  era_12 orbital_weapons_platforms pwr=11136 eff= 557  ptc=0.01
```

Refresh by running `.venv/bin/python scripts/analysis/combat_unit_balance_audit.py`.

---

## Design philosophy in force

After the 2026-05 retune, six distinct group profiles:

1. **Tanks (cost-effective heavyweights)** — `ptc = 0.04` flat across all
   eras. Manpower stays at 1000. Effective power doubles every 1–2 eras.
   The reference baseline.
2. **Cavalry (cost-effective scouts)** — same shape as tanks, `ptc = 0.04`,
   manpower 1000, ~doubling per 2 eras. Slightly lower raw stats than tanks
   per era; the gap is the reconnaissance/occupation utility tax.
3. **Infantry (mass-cheap, declining manpower)** — `ptc` drifts from 0.10
   (era 6) to 0.06 (era 12). Manpower drops from 1000 → 600 → 400 → 250
   across eras 6/10/11/12 — by end-game, an infantry battalion is ~1/4 the
   manpower of a tank battalion, so each "battalion" of infantry pulls a
   smaller share of formation manpower. Combined with vanilla's
   `MILITARY_FORMATION_ORGANIZATION_SPECIAL_UNITS_ADD = -50` floor (>50%
   special units → linear org penalty), late-game players still need to
   field plenty of infantry battalions, but the *manpower* share of
   non-infantry can grow.
4. **Marines (specialty amphibious)** — `ptc` 0.10 → 0.07. Manpower
   decline gentler than infantry: 1000 → 800 → 600 → 500 across eras
   6/8/10/11. Marines stay viable as a default-group "floor" unit
   alongside infantry.
5. **Artillery (offense-heavy specialist)** — `ptc` 0.08 → 0.07 for the
   field-artillery line. Manpower mostly flat (1000 → 800), then drops to
   100 for the two orbital novelty units.
6. **Aircraft (premium-stat force multipliers)** — `ptc = 0.02` flat
   (~half the tank rate). Low manpower (200) means each battalion fields
   few men but at very high raw stats — they let small armies punch above
   their weight, in exchange for being roughly half as cost-effective per
   upkeep dollar as tanks.
7. **Orbital novelty (very strong, very expensive)** — `ptc = 0.01`,
   manpower 100. Orbital bombardment, antimatter strikes, orbital
   tactical vehicles, and orbital weapons platforms. By design 4× less
   cost-effective than tanks; balanced by being load-bearing
   devastation/morale-damage specialists rather than primary combat
   stats.

---

## Validation checks

`mobile_armor` → era 5 chain: the mod's `REPLACE:combat_unit_type_heavy_tank`
sits in vanilla's tanks-group slot at era 5 with raw 62, eff 31, ptc 0.06 —
intentionally weaker than vanilla's mechanized infantry (eff 55) so the
era 7 main battle tank is a meaningful upgrade rather than a sidegrade.

The vanilla special-unit organization penalty (50% by-count threshold,
default groups = infantry + marines, special = artillery + cavalry +
mod-added tanks + aircraft) is the structural floor this balance pass
respects: infantry + marines stay numerous-and-mass-efficient through
end-game so a player can field 50%+ default-group battalions without
giving up too much per-battalion combat power.

---

## Caveats

- **Per-unit power treatment:** `power = offense + defense` is still a
  scalar approximation. Real Vic3 combat weights offense and defense by
  formation role and battle stance. `eff_pwr` is also an approximation
  (the vanilla power-projection formula); per-tick casualty exchange
  involves morale damage, kill rate, and mobilization-option bonuses that
  the audit doesn't model.
- **No interaction with techs:** units' real power scales with
  research-tree modifiers (e.g. `country_unit_offense_mult` from late
  techs), mobilization-option modifiers, prestige goods bonuses, and
  combined-arms trait bonuses (`common/character_traits/combined_arms_traits.txt`).
  The raw `unit_offense_add` value isn't the in-battle number.
- **Combined-arms bonuses untouched:** the mod's combined-arms trait
  system (5%-by-count thresholds, +5%–+8% modifiers per qualifying group,
  full-spectrum +5%/+5% bonus) is a separate balance lever. Magnitudes
  weren't part of this pass.
- **Costs untouched:** `upkeep_modifier` blocks (input goods × prices)
  weren't retuned. The retune lands ptc targets *given* current costs.
  Adjusting costs would need to flow through `pm_costs.py` and the
  auto-generated `# Total cost:` comments.
