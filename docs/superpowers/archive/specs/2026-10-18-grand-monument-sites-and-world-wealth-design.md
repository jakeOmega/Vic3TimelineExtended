# Grand Monuments: construction sites, recorded size, and grandeur that costs more as the world grows rich — design

Status: owner-approved in conversation, 2026-10-18 (written up from it). Builds on the Dedicate button
(branch `feat/gm-dedicate-button`, its own PR), which must land first.

## 1. Intent

A monument is impressive because it was a major project for its time. Building another Eiffel Tower or Arc de
Triomphe in the modern era is not hard (look at Las Vegas), so a level built in a rich world should be worth less
grandeur than the same level built in 1836. The owner's rough model: **two monuments built in different years have
about the same starting grandeur if they cost the same share of world GDP.** In a world ten times richer, a given
grandeur takes ten times the construction. The model doesn't need to hold exactly; it sets the direction.

That makes late monuments much taller in levels, and today a monument's size *is* its building's level. Script can
rebuild a building only up to 200 levels, and Rededicate, carrying off a piece, a returned trophy and a promotion all
rebuild it. So the size moves into the monument's own records, and the building stops carrying it. In the owner's
words: "in hindsight, it is what we should've done in the first place." It retires most of the rebuild machinery of
the last two weeks.

The owner also wants the player to see the difference between a monument being built and a finished one, so the
building splits in two.

## 2. Goals, non-goals, anti-goals

**Goals**

- Starting grandeur is set by world wealth when each level is built, measured against 1836.
- A player can build very large monuments: no level cap.
- Building is pausable, and a monument is finished only when the player dedicates it (the Dedicate button).
- The player sees what a level is worth *before* building.
- Upkeep follows the monument's recorded size, and mothballing really saves money.
- Old saves keep every monument's grandeur.
- The system gets simpler: no rebuild of a finished monument except the one-time migration.

**Non-goals**

- Per-country wealth. The measure is the world's GDP, not the builder's.
- Changing the effect curve, the steps, the dedications' effects, trophies' rules or contests.
- Shrinking a monument from engine-side building damage (war, a nuclear strike halving the building).

**Anti-goals** (failures even if it "works")

- An old save's dedicated monument loses grandeur, effects or its dedication when it loads, or goes undedicated for
  a month while it migrates. (An old save's *undedicated* monument does lose its standing effects, prestige, cultural
  pull and tourism, when it becomes a site; the owner approved that conversion, and Dedicate gives them back at once
  when nothing is queued.)
- Two construction efforts on one monument at once ("pausing is fine, building in parallel is not").
- Half the rebuild machinery removed and half still running: every path that rebuilt a finished monument either
  goes or is shown to be unreachable.
- A rate the player can only learn after spending the construction.

## 3. What the owner decided

### 3.1 Two buildings

- **The construction site** is what a player builds and expands. One per state (the engine allows one building of a
  type in a state). Its levels are the monument being built; the site's building level is the truth until dedication.
  The player may pause it for as long as they like. **While it stands it has no upkeep and no effects.**
- **Dedicate** is available only while nothing on the site is under construction. It opens the ceremony
  (`monument_events.2`). The answer removes the site, records the monument's levels and its starting grandeur, and a
  **finished monument** stands at level 1, or, if one already stands in the state, the new one joins it beside, the
  grander one first, as today (`gm_state_swap_primary`).
- **"Not yet"** (today's "leave it undedicated") leaves the site as it is.
- **The finished monument can never be expanded.** More building in that state means a new site. There is no freeze,
  no "new levels on a finished monument" detection (`gm_state_has_new_levels`, `gm_state_found_beside`, `gm_levels`),
  and no expansion gate on the finished building (`gm_state_can_expand` in its current form).
- **Every finished monument carries a dedication.** There is no finished-but-undedicated monument any more.

### 3.2 Starting grandeur from world wealth

- **The rate:** a level's grandeur is world GDP in 1836 divided by world GDP when it is built
  (`global_gdp_script_value`, `common/script_values/extra_script_values.txt`, already defined). A world ten times
  richer gives each level a tenth.
- **Five a level in 1836** (owner, 2026-10-19, after a 2055 save counted 100 levels at 0.04): the rate is
  `gm_level_grandeur_1836` (5) times that ratio, to the nearest 0.001 and at least 0.001, applied where the rate is
  read (`gm_world_rate_value`), so a save's stored ratio takes it at once. The 1836 landmarks, the trophies abroad in
  1836 and dug-up monuments count at 5 a level too; records already written keep their grandeur. Everything priced
  in grandeur (the effect steps, an opportunity's 5, vanity backlash, trophy infamy) is unchanged, so a level goes
  five times as far toward each.
- **Per level, at the rate of the year it finishes.** Building over decades is rare, so the fallback, the whole
  monument at the rate of its dedication day, is acceptable if per-level tracking proves fiddly.
- **Ageing** adds 2% of *starting* grandeur a year (×0.5 while mothballed, as today), linear, not compounding.
- **Opportunities** ask for grandeur (starting grandeur of the fitting dedication; age still never counts), not
  levels. The gift stays +5 grandeur to age.
- **The player sees the rate before building.** The owner suggested the state panel's monument box. See §5 for the
  places this design adds.

### 3.3 Records instead of rebuilds

- A finished monument's levels, starting grandeur and age live in its records (state variables for the primary, the
  container's `gm_tr_*` for one beside it, as today). Nothing reads the finished building's level for its size.
- Rededicate, carrying off a piece, a trophy coming home, an opportunity's gift and a promotion change the records.
  None rebuilds the building.
- **War damage** to the building doesn't touch the records. Anything meant to shrink a monument changes its records
  and says so in a custom tooltip.

### 3.4 Upkeep

- Worked out from the recorded levels (what the old per-level maintenance would have cost) and charged as an input
  modifier on the finished building, the way the Strategic Reserve hub charges its inputs: the method carries a base
  input and a runtime modifier scales it.
- **Mothballed: no upkeep** (owner, 2026-10-18: "we may even want mothballed to zero it; it is weak now"; the design
  takes zero). Open keeps today's +50%.
- *(my call)* The base input stays on the maintenance method, so under the construction rule's direct and
  no-maintenance settings (`pm_no_maintenance` forced) monuments pay no upkeep, as today.

### 3.5 Old saves and 1836

- A **dedicated** monument is recorded at its current levels, its levels count at the 1836 rate (so its starting
  grandeur equals its levels and it keeps its grandeur), its age is kept, and its building is reset once to a level-1
  finished monument on the same dedication.
- An **undedicated** monument (left undedicated, or a ceremony still open) becomes a site with its levels and gets the
  Dedicate button. Its levels count at the 1836 rate.
- Monuments beside another (containers) and trophies abroad already keep their size in records; they gain a starting
  grandeur equal to their levels.
- **The 1836 landmarks start the game this way**: a level-1 finished monument with its records.
- *(my call)* **A frozen monument migrates at its recorded `gm_levels`**, not at what its building holds, so a
  monument short of levels (the Arc de Triomphe's 11 against 15 in the 1898 crash save) gets them back by being
  recorded. The one-off repair `gm_short_repair_monthly` (#936, due for removal after 2026-12-17) then has nothing to
  do and goes with the migration.

### 3.6 What counts levels and what counts grandeur *(my calls)*

The rule: **what a monument costs to build or keep up counts levels; what it means counts grandeur.**

- Levels: upkeep, Rededicate's money cost, a site's construction.
- Starting grandeur (the share of the world's wealth it took): the effects, opportunities, **vanity backlash** (each
  level finished in hard times draws outrage in proportion to the grandeur it adds, so a project of the same share of
  the world's wealth draws the same outrage in any era; the panel's Hard Times warning follows), **trophy infamy** (on
  the grandeur taken, not its levels), and every share a taking or return moves.
- **Archaeology:** a dug-up monument was built in the ancient world, so its levels count at the 1836 rate
  (`gm_level_grandeur_1836`, five a level since 2026-10-19), like the 1836 landmarks.

### 3.7 Merges, revolts, a lost building

- **Merges** *(my call)*: a merge drops the absorbed state's variables, where the records live, so shadows stay, but
  they carry the records only, with no level arithmetic (`gm_state_unexplained_levels`, `gm_state_levels_short` go).
  An orphaned shadow in a region stands beside the surviving state's monument, or as its primary if it has none; the
  surviving finished building is put back to level 1 if the merge left it taller. A site's grandeur so far is
  shadowed the same way; levels on a site that its records don't explain count at the current rate. What the engine
  does with two level-1 finished buildings, or two sites, in a merge is unread: a `TE_SELF_CHECK`.
- **A lost building** *(my call, from the owner's "war damage doesn't touch the records")*: the finished building
  can't be downsized or demolished by a player (`downsizeable = no`); only script removes it (Pull Down, a whole
  taking). If it vanishes anyway while its records stand, a hidden monthly check puts it back at level 1 on its
  dedication.
- **A revolt keeps the monument whole** (owner, 2026-10-18, replacing the 2026-10-17 call that a split piece takes
  the monument's identity, which rested on the engine dividing the levels): the monument stays with the part of the
  state that keeps its records, and the rebels' part gets nothing. A finished building the engine gives that part,
  with no records, is removed; a site split between the parts is construction, and each part keeps the levels it
  holds (the old part's lost levels take their share of its grandeur so far, §5). The split-piece machinery goes:
  `gm_piece_of`, `gm_split_piece` and its notes, `gm_state_split_pending`, `gm_state_take_split_identity`,
  `gm_sh_rejoin`, the piece-takes-whole paths, `gm_state_forget_split`, and the self-checks
  `monument_split_identity` and `monument_split_rejoined`. A revolution that wins still ends with the winner holding
  the monument (`gm_repair_after_civil_war`).

## 4. Constraints and known engine facts

*Amended 2026-10-18 while building Plan A:* `create_building` does take `activate_production_methods` (the 1836
landmarks already used it), and script does create a `buildable = no` building (vanilla's Manila cathedral ruins), so the
finished type is `buildable = no` and the dedication creates it on its method, with `gm_restore_pm` as the fallback and
`TE_SELF_CHECK monument_created_on_dedication` reading which one did the work. Where the points below call these
unverified, read them as settled by that.

- **One building of a type per state.** A state holds at most one site and one finished building. Monuments beside
  another stay containers (`gm_monument`, `gm_monuments`), as in the 2026-10-13 and 2026-10-16 specs.
- **The site's building type is new; the finished one keeps `building_grand_monument`**, so an old save's buildings
  are already the finished type and only their level and records change.
- **`create_building` checks some of a building's requirements since 1.13.9**, and whether that includes
  `can_build_government` is unverified (`scripting_best_practices.md`; the `te_cm_placing_site` pattern; today's
  `gm_rebuilding` hold). Players must not be able to build the finished type, but script must always be able to.
  Needs a `TE_SELF_CHECK`.
- **A new building starts on the methods most of its owner's buildings of that type use** (the engine's copy,
  `gm_effects.txt` § "The engine's copy"), and a method switched in an effect can't be read back in the same effect.
  The finished building created at dedication needs its dedication's method; whether `create_building` can take
  methods directly is unverified, and today's `gm_restore_pm` path is the fallback. Two switches in one tick listed a
  dedication twice in a save.
- **Removing a site with construction queued** would probably cancel the queue. The Dedicate gate (nothing under
  construction) avoids it; a migration that turns an old monument with queued levels into a site must wait for its
  construction to stop, or keep the building.
- **Building-scoped modifiers with `multiplier =`** must be refreshed from a building or state pulse, one refresh site
  (CLAUDE.md, dynamic-modifier pattern; #500's lesson).
- **The refresh runs inside tooltips** and writes nothing reliably; removals, creations and migration run from hidden
  events (`monument_events.29`/`.30`/`.31` pattern).
- **A revolution's winner inherits variables, not modifiers or lists.** Records stay in variables; the upkeep modifier
  is rebuilt by its refresh.
- **AI:** dedicates once nothing is queued (the Dedicate button PR's rule). The AI's opportunity queue
  (`gm_com_ai_queue`, `gm_com_queue_levels`) builds on the site, levels = missing grandeur ÷ the current rate,
  rounded up.

## 5. Left to the builder (with the calls made in writing this)

Calls made by me in writing this up, not the owner's; listed for the owner's check:

- **The 1836 baseline is a fixed constant** (world GDP at the 1836 start, measured once from a fresh game), not
  recorded per game, so old saves get the right rate. A mod that changes the economy shifts it; accepted.
- **The rate is updated once a year** (1 January, a global variable) with no smoothing. A depression year makes
  monuments cheaper in grandeur terms; accepted.
- **Where the rate shows before building:** the site's card in the state view (a line: a level finished now adds X
  grandeur), a line in the Grand Monuments tab's national section, and the site building's description in the build
  menu if the engine renders it (unverified: play-test list).
- **A site counts toward the six-monument limit** of a state; it can't be started while six stand.
- **A site's lost levels** (the player downsizes it, or war damage to the site) take their share of the grandeur
  accumulated so far.
- **Rededicate** halves levels, starting grandeur and age and keeps its money cost (500 × recorded levels); no rebuild.
- **A taken piece** carries its share of levels, starting grandeur and age; a return brings them back.

The rest is the builder's: names, where the rate is computed, how the per-level weighting is tracked (a monthly
level difference on the site is the obvious way), how the upkeep modifier is built, the migration's order and its
self-checks, which machinery to delete (the 200-level ladder for monuments, `gm_rebuilding`, `gm_tr_return_queued`,
one-rebuild-a-day, `gm_restore_pm` where no rebuild needs it, `gm_levels` and found-beside), the GUI for the site's
card and the national line, the tests (`test_grand_monument_registry.py`'s `CONTAINER_RECORDS`, `LevelsApartTests`,
the layout tests), the loc, docs (`docs/systems/mod_systems.md` § Grand Monuments), the play-test list and the player
guide chapter.
