# Naval modules play-test checklist

What the next play-test should look at in the ship modules sized to their hull (2026-11-03; design
`docs/superpowers/specs/2026-11-03-ship-module-scaling-design.md`). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

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
