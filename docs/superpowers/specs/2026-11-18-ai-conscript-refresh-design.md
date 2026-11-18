# AI conscript refresh: clearing conscription centres whose conscripts are eras out of date

Status: design, 2026-11-18. Refs #1877 (trap 5).

## Why

The owner, 2026-11-18, on the AI's Irregular Infantry: "they don't contribute much to their combat forces but still take casualties. So they are just throwing their people away", and asked whether 1960s armies still read as musket levies: "yes, this - and worse the later it gets".

What the saves show (the owner's USA game, 1946 and 1964; #1877's trap 5 correction):

- The irregulars are conscripts. Among the 20 largest AI economies in 1964, 4% of barracks battalions are Irregular Infantry, against 38% of conscription-centre battalions. The standing armies are modern.
- The AI keeps each formation's default unit types at its best unlocked type (81 of 95 top-20 formations at Armored Infantry in 1964), so new conscripts come in modern. It never upgrades the conscripts it already has: Japan's 100 conscripts were the same in 1946 and 1964, half of them irregulars.

## The engine facts it rests on (measured 2026-11-18, run `20261118T193355Z`)

- No effect changes a battalion's type, disbands one or removes a formation.
- `remove_building = building_conscription_center` in a state removes the centre and deletes its conscript battalions (a Dutch state's 39, a Chilean state's 3; formation totals fell by exactly those).
- An AI at peace rebuilt both centres within a month, in its formations' default types (17 Motorized Artillery and 19 Light Tanks; 3 Armored Infantry), and both held two months later.

Recorded in `docs/guides/scripting_best_practices.md`. Two countries in one save: the rest is the self-check's.

## Goals

- AI conscript pools stop holding battalions far behind what the country can field, so that a raised conscript fights at its era's level.
- Each pool turns over within about a year of going out of date, and the change shows in the next observer or played game.

## Non-goals

- The player's conscripts. The player sees and upgrades them in the formation panel, and may keep cheap ones on purpose.
- Standing armies (barracks battalions): the AI keeps them current already.
- A new guerrilla unit type. The AI rebuilds into its formation's defaults, which it sets to its best unlocked type, so it would not choose a cheaper one. It could come later as a player option, on its own merits.

## Anti-goals

- Clearing a centre while its conscripts may be needed: at war, with any formation mobilized, or in a diplomatic play. That would delete raised troops, or leave a country short of them as a war starts.
- Clearing the same centre over and over, if the AI rebuilds old types there.

## Approaches considered

1. **A yearly peacetime clear-out for AI countries** (chosen by the owner, 2026-11-18). Remove the conscription centres whose conscripts are eras out of date; the AI rebuilds them in modern types. It reaches the pools that exist now and needs no change to the AI's choices. Costs: raised modern conscripts buy goods where irregulars bought none, and the rebuild follows the formation's defaults, so the mix of unit groups can change (the Dutch state's rebuild had no infantry).
2. **A guerrilla unit type**: cheap, technology-unlocked, open to conscripts. Set aside: the AI would not pick it (above), and it would not reach the existing pools.
3. **Irregulars strengthened by technology** (per-type stat modifiers granted by technologies): fewer wasted lives, but the AI still fields "Irregular Infantry" in 1965. Set aside: it misses the owner's main point.

## The design

- **Who and when.** Each AI country (`is_ai = yes`), once a year (the country's yearly pulse), when it is not at war, no formation of its is mobilized, and it is neither a committed nor an undecided participant in a diplomatic play.
- **Which centres.** Each state the country owns that has a conscription centre holding at least one stale battalion, and whose centre this pass has not cleared in the last five years.
- **Stale.** A battalion whose type is three or more eras older than a type of the same unit group (infantry, cavalry, artillery, tanks, marines, aircraft) that the country has unlocked. A type's era is the era of its unlocking technology; Irregular Infantry, which no technology unlocks, counts as era 0. At three eras:

  | Type | Stale once the country has unlocked |
  |---|---|
  | Irregular Infantry (0), Line Infantry (1) | Trench Infantry (4) or later |
  | Skirmish Infantry (2) | Squad or Mechanized Infantry (5) or later |
  | Hussars, Dragoons, Cuirassiers, Lancers (1) | Light Tanks (5) or later |
  | Cannon and Mobile Artillery (1) | Siege Artillery (4) or later |
  | Shrapnel Artillery (3) | Motorized Artillery (6) or later |
  | Low-tier Marines (1); Mid-tier Marines (2) | High-tier Marines (4); Combined Arms Marines (6) |

  Later types follow the same rule (Siege Artillery once Guided Artillery Projectiles are unlocked, Heavy Tanks once Reactive Armor Tanks are). The rule is derived from the unit-type and technology data, not written by hand, and a test holds the trigger to that data, so a new mod unit type joins it.
- **What it does.** `remove_building = building_conscription_center` in that state, and a note on the state of when (for the five years).
- **Self-check** (`TE_SELF_CHECK … ai_conscript_refresh`, once a game). The first centre the pass clears is followed. Three months later: OK when the state has a conscription centre again with at least one battalion and none of them stale; BROKEN when it has none (fallback: stop clearing and take this to the owner) or when the rebuilt battalions are stale again (fallback: the AI's defaults are not current for that country; skip countries whose formations default to a stale type). The line prints the counts before and after and the country.
- **Play-test rows** (the AI economy list or a military one): conscripts by type among the 20 largest AI economies before and after, read from a save as #1877's correction did; goods shortages in wars where modern conscripts were raised; the infantry share of the rebuilt pools; whether Russia's growing irregular pool (272 to 424, 1946 to 1964) is from somewhere the pass does not reach.
- **Docs.** A section in `docs/systems/mod_systems/ai.md`. The player guide very likely needs no change (an AI's housekeeping, below the guide's level of detail); the PR body says which.

## My calls in this design (the owner may correct any)

- AI only, with no game rule of its own: it is AI housekeeping, like #1880's construction pass.
- Three eras behind as the line, so a country is not churned for being one tier behind.
- Any stale battalion clears its centre: the rest are rebuilt in a month at peace.
- Five years before the same centre is cleared again.
- All of a country's stale centres in the same year, not one at a time.

## Left to the builder

The trigger names; how the stale rule is derived (a generator writing the trigger, or a trigger checked by a test against the data); file placement; how the self-check follows its state.
