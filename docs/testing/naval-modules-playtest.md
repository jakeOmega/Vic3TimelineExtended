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
| **Old ships.** Load a save from before the update that has a built Marine Assault Ship. Read its armor and supply, and whether its template asks for a retrofit. | About 140 armor and 440 supply, at once or after a retrofit. | About 70 armor and 255 supply: the ship kept the base-game Troopship's modules on its new, smaller hull. Ten ship types that used to borrow a set are exposed (the three troop ships worst, about half their armor); a retrofit should fix them, so say so in the release notes. If no retrofit is offered, note what the template shows. |
| **Old templates.** Load a save with a mod ship designed before the update. | The ship keeps fighting; its template asks for a retrofit or shows the new modules. | A ship with no modules or a broken template: note which, and whether a retrofit fixes it. |
| **AI.** Watch an AI at war in the 1990s or later; note which module tiers its late ships carry. | Medium or high, as before. Module `ai_weight` is unchanged (1/2/3 times the market multiplier), so the AI's choice shouldn't move. | Mostly light: AI late navies are now weaker than before, since a light module buys less than it did. |

## Utilities and accuracy (PR #1389)

The load-bearing unknown: how the engine combines a target's `ship_suffered_accuracy_mult` (built-in defense plus a
countermeasure) with the attacker's own accuracy bonuses. Multiplied, or added into one sum? The offline budget
(`test_ship_modules.py`, `test_accuracy_budget`) keeps either reading safe in calm water; the battle log tells which it
is. Counts assume calm water, medium propulsion on the target, and an attacker with Naval Fire Control Systems,
Precision Guided Munitions and Network Centric Warfare (+25% accuracy). Anti-Submarine Warfare adds +30% against
submarines, so the Submarine row gives both.

| Check | Expect (multiplied / added) | If it fails |
|---|---|---|
| **Escort.** An Arsenal Ship fleet against Networked Air Defense Cruisers without a countermeasure; count the Arsenal Ships' misses in the log. | About 29% / 23% misses. | Nearly no misses: the built-in defense is ignored. Check the cruiser's tooltip shows the −25%. |
| **Countermeasure.** The same, with the cruisers fitting the Close-In Weapon System. | About 51% / 41% misses. | The same as the row above: the module's suffered accuracy is ignored. |
| **Submarine.** Arsenal Ships against Stealth Attack Submarines, then with the submarines on Camouflage. Note whether the attacker has Anti-Submarine Warfare. | Without it: about 40% misses, then 49% / 54%. With it: about 13%, then 26% / 27%. | About 5% either way: the capitals' −60% against submarines is ignored. Near 90%: the sum went negative under the added reading; lower the −60%. |
| **Old fleet.** The Arsenal Ships against base-game ships. | Almost every shot hits. | |
| ~~**Successors.** Hover Damage Control Teams; read debug.log after loading.~~ | ~~The tooltip names Fire Suppression as incompatible; no `incompatible_with` line in debug.log.~~ | Failed: the engine swallowed each module's effects after the key (eleven utilities showed only goods). The key is removed; the shared slot keeps a successor and its predecessor apart (fix PR, 2026-11-04). |
| **Effects.** Hover each new utility in the designer. | Its effects are listed (Close-In Weapon System: −20% suffered accuracy, −60% vulnerability), and debug.log has no `Failed to read key reference` line for `extra_utility_modifications.txt`. | Only goods listed: a key in the module is breaking the reader; the debug.log line names the file and line. |
| **Slots.** Open an Antimatter Battleship's designer, then a Nuclear Supercarrier's. | Three utility slots on the battleship: protection, countermeasures, and weapons, sensors and support. Two on the carrier, with Extended Sick Bay among the protection and countermeasure modules. | |

## Vulnerability and screening rescale (#1625)

The mod's ships moved to vanilla 1.14.5's vulnerability and screening scale (about ×0.56; mapping in the
`extra_ship_types.txt` header). Vulnerability weights which ship an attacker fires at and screening shields the
rest, so the offline tests can pin the numbers but not how a battle now goes. Totals below are hull plus medium
guns; `vulnerability_exploitation` is still unset on every mod ship (it exploits everything).

| Check | Expect | If it fails |
|---|---|---|
| **Designer.** Read an Arsenal Ship's and a Networked Air Defense Cruiser's stats with medium modules. | Arsenal Ship vulnerability 125, screening 5; the cruiser 25 and 278, plus 111 with Aegis Air Defense. | The old 225 / 61: the deploy is stale. |
| **Mixed battle line.** A fleet of Arsenal Ships and base-game Super Dreadnoughts in battle; count the hits each class takes in the log. | About the same hits per ship (both 125). Before the change the Arsenal Ships drew about 1.8 times as many. | |
| **Escorts.** A fleet of Networked Air Defense Cruisers and base-game Light Cruisers. | The mod cruisers take about 5 times the hits per ship of a Light Cruiser (25 against 5), down from about 12. | |
| **Unescorted capitals.** Mod capitals with no escorts against a late attacker (Super Dreadnoughts, which exploit up to 140); then the same with three Pulsed Laser Escorts. | The escorts take a real share of the fire and the capitals' losses drop, as Light Cruisers shield Dreadnoughts. | The capitals lose as much with escorts as without: note the battle log's screening figures for both fleets. |
| **Transports.** An escorted invasion fleet: 4 capitals, 4 Pulsed Laser Escorts and 4 Marine Assault Ships. Read the formation panel's screening ratio, then send it into battle. | The screening ratio is about what it was before the change (1.12 with medium guns; the troop ships were rescaled with the capitals for this). The transports draw about the share of fire they did before (147 against the capitals' 125, as 245 against 225). | A ratio near 0.84: the troop ships' values did not deploy. Transports lost in nearly every battle: compare with a fleet of base-game Troopships. |
