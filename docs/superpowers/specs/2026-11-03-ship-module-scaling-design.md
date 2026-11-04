# Ship modules that scale with the era — design

Date: 2026-11-03. Owner request: the mod's ship modifications should, generally,
be more expensive and more powerful the later in the tech tree they unlock. The
review that started this compared every module the mod adds with the base
game's; its numbers are below.

## Why

Two separate problems, pulling in opposite directions.

**Core slots (armor, guns, propulsion, range).** The base game sizes each hull's
modules to the hull: on most base-game hulls, guns-high adds about 2× the hull's
own damage and armor-high about 3× its armor, so going from light to high
modules buys about +65% hull damage, +150% armor and +35% hit points. The mod's
module sets copied their base-game parent's flat values ("Modifier values match
the vanilla parent's") onto hulls up to 16× stronger, and ten of the nineteen mod
hulls reuse another hull's set. Light to high now buys +7% hull damage on the
Antimatter Battleship, for five times the goods of the Super Dreadnought's guns.

**Utilities.** The base game's eleven utilities are percentages, which grow with
the hull, cost 100–500 in goods, and need no technology (Torpedo Nets needs one
from era 3). The mod's eight unlock in eras 6–11 and cost 580–4,600, but most
give smaller percentages than a base-game module on the same stat in the same
hull's list (Composite Armor Plating −15% hull damage taken against Fire
Suppression's −25%; DEW Point Defense −25% vulnerability against Torpedo Nets'
−50%).

**Accuracy.** The hit formula (1.14.5 defines): miss chance = 0.5 + 0.03 ×
(target speed − target visibility / 15 − 5 × accuracy), clamped to 5–90%. Mod
hulls carry accuracy 16–30 against target speeds of 27 or less, so 291 of the 361
mod-against-mod pairings already hit 95% of the time in calm water and 243 in
fog. Every accuracy bonus a module sells does nothing in a late war.

## Decisions (the owner's)

1. Core slots: **rebalance at medium.** Keep each hull's total with medium
   modules where it is; move strength from the hull into the modules until light
   to high buys what it does in the base game.
2. Utilities: **successors**: each mod utility succeeds the base-game module on
   its stat, with a bigger percentage, more goods and `incompatible_with` its
   predecessor. Add successors for Advanced Explosives and Fire Suppression, and
   size flat parts to late hulls or turn them into percentages. **Prune** a
   superseded base-game module from late hulls where it no longer makes sense
   (the owner's example: torpedo nets).
3. Accuracy: modern ships should be accurate; give modern hulls defenses as a
   standard part of the hull rather than asking the player to stack modules to
   −75%. Improve it this pass; a later pass can finish it.
4. Stacking: restrict which modules go in which utility slot.

## Calls I made (the builder's), for the owner to check

1. **Accuracy uses the levers with known math, not large defense multipliers.**
   Built-in defenses big enough to pull accuracy 16–30 into the range where the
   formula moves (effective accuracy about 1.5–7) would be −80% or more, and at
   that size a 5-point module halves what's left: the confusing knife edge the
   owner wanted to avoid. Instead:
   - Mod hull accuracy comes down to the base game's level: 6–8 for the combat
     ships, rising a little with era (capitals 6, 6, 7, 8; escorts 6, 7, 6;
     submarines 7, 7, 8; the ASW Destroyer and Guided Missile Ship 7), carriers
     unchanged at 18 and 20 (the base game's carrier has 20), troop ships
     unchanged. The calibration showed a ladder of 8–11 still leaves almost
     every pairing at the cap, because the mod's naval technologies add +10% to
     +35% accuracy fleet-wide. That is where "modern ships are accurate" now
     lives: modern ships still hit the base game's at the cap.
   - Mod capitals get the base game's own penalty for firing at small, fast
     ships, against the mod's torpedo craft: −50% (the Dreadnought carries −66%
     against torpedo craft and −50% against destroyers; −50% leaves room in the
     budget below for a countermeasure), and −60% against submarines, which
     leaves room for Camouflage. The attacker-side penalties some hulls carried
     against the Pulsed Laser Escort and Swarm Coordination Vessel (up to −40%)
     go: the escorts' own defense replaces them.
   - Cruiser escorts carry a modest built-in defense (`ship_suffered_accuracy_mult`
     −25% on the Networked Air Defense Cruiser, −30% on the Pulsed Laser Escort
     and Swarm Coordination Vessel: "point defense as standard"), so the
     Close-In Weapon System, Electronic Countermeasures and DEW Point Defense
     work at sizes a player can read (−20% to −35%).
   - Target: capital against escort, capital against submarine and escort
     against escort leave the 95% cap; capital against capital may stay near it.
     Measured with default (medium) designs and each era's naval technologies,
     multiplicative reading: mod-against-mod pairings at the 5% miss floor go
     from 333 of 361 to 279 in calm water (285 to 192 in fog), and the pairings
     where a countermeasure moves miss chance by 10 points or more from 21 to
     111 (17 to 200 in fog). Medians, without and with the target's best
     countermeasure: capital against escort 23% / 57%, against destroyer
     22% / 33%, against submarine 37% / 46%, escort against escort 22% / 62%.
     The base game's era-5 fleet: capital against cruiser 29%, against
     destroyer 75%, against submarine 52%, cruiser against cruiser 29%.
   - Guards, because the engine's rule for combining a target's suffered
     accuracy with an attacker's accuracy bonuses is undocumented: no single
     target-side term (a hull's built-in defense, a module) below −0.4, and no
     attacker/target pairing whose negative terms sum below −0.8 (if the engine
     adds them and the sum goes negative, the attacker misses 90% of the time
     with no log line).
2. **The reshape uses each hull's base-game class analogue** (the same mapping
   the power projection derivation in `extra_ship_types.txt` uses): capital ships
   the Super Dreadnought, cruiser escorts the Light Cruiser, the ASW Destroyer and
   Guided Missile Ship the Destroyer, carriers the Aircraft Carrier, submarines
   the Submarine, troop ships the Troopship. A stat's medium total T splits as
   the analogue's does: hull = T × h / (h + m), tier = T × tier / (h + m), with h
   and m the analogue's hull and medium-module values.
3. **Reshaped stats:** hull and crew damage (guns), armor and hit points (armor),
   supply capacity and power projection (range). The base game's range modules
   add power projection and the mod's added none; at medium it now moves out of
   the hull into the module, so a default ship's prestige is unchanged. Speed,
   critical hits, vulnerability, visibility and each set's extras are not
   reshaped: speed doesn't grow with the era the way damage does, the critical-hit
   tiers are the #223 anchors, and vulnerability waits on the open 1.14.5
   vulnerability/screening decision.
4. **Every mod hull gets its own module set.** Sized modules can't be shared
   between a 1,500- and a 2,800-damage hull, so the ten hulls that borrowed a set
   get their own (120 new modules). Their names and descriptions are spliced from
   the set they borrowed (`"$ship_mod_arsenal_ship_armor_light$"`); their goods
   are the borrowed set's, scaled by the ratio of the two hulls' construction
   goods. The nine existing sets keep their goods.
5. **Rounding:** damage and armor to 5 (1 below 50), hit points to 25, supply to
   5, power projection to 1. Medium totals land within 2% of today's.
6. **Utility slots get roles.** Protection (hull and crew damage taken),
   countermeasures (accuracy against the ship, vulnerability, visibility),
   weapons, sensors and support. A one-slot hull lists everything it mounts; a
   two-slot hull takes protection and countermeasures in one slot and the rest
   in the other; a three-slot hull one slot each for protection,
   countermeasures and the rest. Each module appears in exactly one slot per
   hull, so no module can be fitted twice and no two damage-taken reducers
   stack, whatever the engine allows.
7. **The four late capitals get a third utility slot** (Arsenal Ship, Stealth
   Battlecruiser, Hypersonic Missile Platform, Antimatter Battleship), as the
   Super Dreadnought has.
8. **Pruned from mod hulls:** Torpedo Nets (anti-torpedo nets were abandoned
   after the First World War) and Searchlights (radar replaced them). Both stay on
   the base game's hulls. Every other base-game utility stays as a cheaper,
   weaker option.
9. **The Pulsed Laser Escort's guns-high +50 accuracy becomes +30% accuracy**;
   +50 is several whole base-game hulls' worth and would saturate once accuracy
   matters.
11. **Utility lists per ship** follow the old lists: the successor is added
    wherever its predecessor was listed, Torpedo Nets give way to the
    Close-In Weapon System and Searchlights to Surface Search Radar. Submarines
    get no Close-In Weapon System, Electronic Countermeasures or DEW Point
    Defense: with the capitals' −60% against them, only Camouflage fits the
    accuracy budget.
12. **Utility icons** use the base game's naval icons by role (armor for
    protection and point defense, damage for weapons, marines for the
    Helicopter Pad, supplies for Underway Replenishment) rather than the one
    accuracy icon every mod utility used.
10. **Flat parts:** screening and detection stay flat (capitals have 10–30
    screening and escorts 250–700, so a percentage would do nothing on the ships
    that need it most), sized to late hulls. Armor, supply capacity, carrying and
    marine capacity become percentages.

## The utility roster

Successors are `incompatible_with` their predecessor. "New" is added by this
work.

| Role | Module | Unlock | Effect | Succeeds |
|---|---|---|---|---|
| Protection | Fire Suppression (base) | — | −25% hull damage taken | |
| Protection | Damage Control Teams (new) | Naval Convoy Defense (6) | −35% hull damage taken, −15% crew damage taken | Fire Suppression |
| Protection | Composite Armor Plating | Modern Material Science (11) | −45% hull damage taken, −40% critical hits taken, +20% armor | Damage Control Teams, Fire Suppression |
| Countermeasures | Camouflage (base) | — | −15% accuracy against the ship, −25% visibility | |
| Countermeasures | Close-In Weapon System (new) | Precision Guided Munitions (8) | −20% accuracy against the ship, −60% vulnerability | Torpedo Nets, Camouflage |
| Countermeasures | Electronic Countermeasures (new) | Electronic Warfare (10) | −30% accuracy against the ship, −40% visibility | Camouflage |
| Countermeasures | DEW Point Defense | Directed Energy Weapons (11) | −35% accuracy against the ship, −70% vulnerability, +200 screening | Close-In Weapon System, Torpedo Nets |
| Weapons | Advanced Explosives (base) | — | +50% critical hit chance, +25% crew damage | |
| Weapons | Precision Warheads (new) | Guided Missiles (7) | +75% critical hit chance, +40% crew damage | Advanced Explosives |
| Weapons | Ballistic Missile Bay | Precision Guided Munitions (8) | +35% hull damage, +60% blockade | Large Carronades, Patrol Boats |
| Weapons | Range Finder (base) | — | +20% accuracy, +20% screening | |
| Weapons | Drone Complement | Swarm Technology (11) | +40% accuracy, +40% screening, +200 detection | Range Finder |
| Weapons | Fire-Control System (base) | — | +10% readiness, +20% accuracy against torpedo craft | |
| Weapons | Aegis Air Defense | Network Centric Warfare (9) | +20% readiness, +200 screening, +40% accuracy against missile ships | Fire-Control System |
| Sensors | Surface Search Radar (new) | Radar (6) | −75% battle-condition accuracy penalty, +50% detection | Searchlights |
| Sensors | Sonar Suite | Sonar (6) | +50% accuracy against submarines, +100 detection | |
| Support | Landing Skiffs (base) | — | +20% naval invasion efficiency | |
| Support | Helicopter Pad | Rapid Deployment Forces (9) | +40% naval invasion efficiency, +25% marine and carrying capacity | Landing Skiffs |
| Support | Underway Replenishment | Containerization (8) | +40% supply capacity, +25% supply efficiency, +30% distance from port | |
| Support | Extended Sick Bay (base) | — | −50% crew damage taken | |

A successor costs more goods than its predecessor and is stronger on every stat
they share. A hull lists the successor wherever it listed the predecessor.

## Delivery

Two PRs, both against `main`:

1. **Core-slot rebalance**: the reshape, the 120 new modules and their
   localization, `test_ship_modules.py` (medium totals against the pre-change
   goldens, light-to-high spread against the analogue, every mod hull on its own
   set), header and best-practice docs, the balance snapshot and the player
   guide. Mechanical and test-backed.
2. **Utilities and accuracy**: the roster, slot roles, the third capital slot,
   pruning, the accuracy ladder, capital penalties and built-in defenses, with
   their tests and the guide's utility table.

## Play-test list (nothing here gates a merge)

- Saved ship templates on mod hulls: pruning Torpedo Nets and Searchlights and
  moving utilities between slots can invalidate a template saved before the
  update.
- One battle log against the expected hit rate for a named pairing, under the
  multiplicative and the additive reading of `ship_suffered_accuracy_mult`:
  `docs/testing/naval-modules-playtest.md`.
- The AI designs late ships with high-tier modules more often than it did
  (its scoring sees the bigger module values).
