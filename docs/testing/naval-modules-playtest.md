# Naval modules play-test checklist

What the next play-test should look at in the ship modules sized to their hull and the utility and accuracy rework
(2026-11-03; design `docs/superpowers/specs/2026-11-03-ship-module-scaling-design.md`). In-game checks do not gate a
merge (CLAUDE.md, "In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what
only the game can show here. Each PR adds its own section, newest last, and a fixed item is struck through with the
commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The ship designer (a module's tooltip, the ship's stat totals), a naval battle's log (each attack
  is listed as a hit or a miss), and the fleet panel.
- **Getting the ships.** Network Centric Warfare and Rapid Deployment Forces (era 9) unlock the Arsenal Ship, the
  Networked Air Defense Cruiser and the Stealth Attack Submarine; grant the technologies from the console in a late
  start rather than playing up to them.
- **Logs.** Read `debug.log`, not `error.log`.

## Core-slot modules (PR #1387)

| Check | Expect | If it fails |
|---|---|---|
| **Totals.** Design an Arsenal Ship with medium modules in all four core slots; read hull damage, armor and hit points. | About 1,310 hull damage, 670 armor, 13,150 hit points (its pre-change strength). | A different total means the engine adds a module to the hull another way than the sum: compare with a base-game Super Dreadnought (170 + 210 = 380). |
| **Spread.** Switch its guns from light to high. | Hull damage 980 → 1,635. | |
| **Old templates.** Load a save with a mod ship designed before the update. | The ship keeps fighting; its template asks for a retrofit or shows the new modules. | A ship with no modules or a broken template: note which, and whether a retrofit fixes it. |
| **AI.** Watch an AI at war in the 1990s or later. | Its late ships carry high-tier modules more often than before. | |

## Utilities and accuracy (PR 2)

The load-bearing unknown: how the engine combines a target's `ship_suffered_accuracy_mult` (built-in defense plus a
countermeasure) with the attacker's own accuracy bonuses. Multiplied, or added into one sum? The offline budget
(`test_ship_modules.py`, `test_accuracy_budget`) keeps either reading safe; the battle log tells which it is. Counts
assume calm water, medium propulsion on the target, and an attacker with Naval Fire Control Systems, Precision Guided
Munitions and Network Centric Warfare (+25% accuracy).

| Check | Expect (multiplied / added) | If it fails |
|---|---|---|
| **Escort.** An Arsenal Ship fleet against Networked Air Defense Cruisers without a countermeasure; count the Arsenal Ships' misses in the log. | About 29% / 23% misses. | Nearly no misses: the built-in defense is ignored. Check the cruiser's tooltip shows the −25%. |
| **Countermeasure.** The same, with the cruisers fitting the Close-In Weapon System. | About 51% / 41% misses. | The same as the row above: the module's suffered accuracy is ignored. |
| **Submarine.** Arsenal Ships against Stealth Attack Submarines, then with the submarines on Camouflage. | About 40% misses, then 49% / 54%. | Near 90% misses: the sum went negative under the added reading; lower the capitals' −60% against submarines. |
| **Old fleet.** The Arsenal Ships against base-game ships. | Almost every shot hits. | |
| **Successors.** Fit Fire Suppression in one slot, then try Damage Control Teams in another. | The designer refuses the second. | `incompatible_with` is one-way: declare it on the base-game module too (an INJECT into vanilla's utility file). |
| **Slots.** Open an Antimatter Battleship's designer. | Three utility slots: protection, countermeasures, and weapons, sensors and support. | |
