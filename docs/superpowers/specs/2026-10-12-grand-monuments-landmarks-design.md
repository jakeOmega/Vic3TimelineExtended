# Grand Monuments v2 phase 4: landmarks standing in 1836 — design

**Date:** 2026-10-12
**Status:** approved in conversation (2026-10-11 and 12), and as a whole by the owner on 2026-10-12
**Builds on:** `2026-10-05-grand-monuments-v2-design.md` (§4, §10; "v2" below), `2026-09-27-grand-monument-rework-design.md`
(§1.1 named landmarks; "v1"), and the pictures spec, *Grand Monument pictures, forms and styles* (2026-10-11, written
in another session and not yet merged).
**Replaces:** v2 §4's table, and its plan to offer landmarks in the style choice (`monument_events.11`).
**Extended by:** `2026-10-12-grand-monument-loot-and-1836-trophies-design.md` (rows 24–51: nineteen landmarks to loot,
and nine never placed, for the trophies of 1836).

## Context

v2 phases 1–3 shipped in #759: the numbers, commissions with names, and the monument policy. Phase 4 places the Grand
Monuments that stood on 1 January 1836, so the world starts with some. Each is a **landmark**: a real monument with its
own name and, in time, its own picture. Their owners' journal entries open on day one. Some of these monuments will
later be contested, conquered, or (from phase 5) carried off as trophies.

Phase 4 builds the landmark mechanism. If phase 6 (historical commissions) is built later, it reuses that mechanism.

## Decisions (owner, 2026-10-11 and 12)

| Question | Decision |
|---|---|
| Order | Phase 4 is built **after the pictures PR**: both change `FORMS`, the `gm_state_form_fits_*` triggers, `test_grand_monument_registry.py` and `gm_name_effects.txt`. Then phase 5 (trophies). Phase 6 (historical commissions) stays in the plan, unscheduled |
| What a landmark is | **Its own skin**, `landmark_<key>`, with one form from the existing roster. The pair gets its own picture, and the monument carries its historical name |
| Locked | **A landmark keeps its skin and form, and so its picture, while it stands**: through contest, heritage, Rededicate, conquest and civil war. Pull Down, or demolition from the building panel, ends it |
| Its name | Kept through contest, heritage, conquest and civil war. **Rededicate gives it a new name by default** (§3.3): "Alexander Column — To the Republic" reads wrong. The namesake choice offers the historical name back |
| The civic-progress technologies | Removed from the three dedication methods that carry them, and checked in the ceremony and at first sight instead (§6). A method whose technology the owner lacks is switched away by the engine (owner, 2026-10-12) |
| Picture codes | Landmarks start at **1,000,000**, in `LANDMARKS` order: append-only, like the pictures spec's codes |
| Before its icon exists | It shows a **stand-in picture**: an existing skin and form pair named in its row |
| Who gets one | Minor countries too, not only the great powers |
| Arc de Triomphe | Level 15. It is the largest triumphal arch ever built (only Pyongyang's 1982 copy is larger) and the most famous monument on the list. It is neither the world's grandest structure of 1836 nor its tallest monument |
| Ancient monuments | Those that still had political or cultural weight in 1836 come first. Aksum, where Ethiopia's emperors were still crowned, qualifies. **Revised (owner, 2026-10-12):** one without that weight may still stand as a heritage site; it is lower priority, all else equal, not excluded. (This is "heritage" in the ordinary sense, not the Heritage status: a To the Nation monument is never contested, and the monthly check lifts Heritage from any monument whose dedication fits.) |
| People and events after 1836 | **No landmark refers to one.** That bars most phase-6 candidates (Appendix B). An exception is an event the game itself scripts: Victoria's accession in 1837 is an event, so a Victoria Memorial would be acceptable |
| Phase 6 (if built) | No great/major-power gate. **All upside:** declining or missing a historical commission costs nothing, because a small power may not afford one |

Two calls made in writing this spec, approved by the owner on 2026-10-12:

1. **Rename and Name It are greyed out while a landmark carries its historical name** ("A landmark keeps its
   historical name"), so the Arc de Triomphe can't become "the Paris Arch". Once a rededication has renamed it, both
   work as for any monument.
2. **The AI preserves a contested landmark more readily** (§5.3), as history mostly did: the Soviets kept the Alexander
   Column.

## Engine facts this rests on

- **`create_building` takes `level` and `activate_production_methods`** in effect scope. The Rededicate ladder
  (`te_construction_market_build_specified_level`) uses `level`. `extra_decisions.txt` uses `activate_production_methods`,
  with a `# REVIEWED` comment for the audit that flags the key. Since 1.13.9 it checks the building's unlocking
  technology. `building_grand_monument` has none.
- **Three dedication methods have a technology:** `pm_monument_artistic` and `pm_monument_naturalist` need Romanticism,
  and `pm_monument_scientific` needs Empiricism. **The engine switches a building off a method whose unlocking
  technology the owner lacks**, onto another allowed one (owner, 2026-10-12). Five landmarks are civic-progress
  buildings, and several owners won't have the technology in 1836. Under the ratchet the dedication may have no allowed
  alternative, so the outcome is uncertain either way; §6 removes the question.
- **A game rule read during history can still change in the lobby.** `on_game_started_after_lobby` (ROOT none) runs once
  the rules are final, which is how the construction market converts what history placed
  (`scripting_best_practices.md` § "Gating a Mechanic on a Game Rule…"). Landmarks are placed there, behind
  `gm_system_enabled`.
- **A new building copies its siblings' dedication**, and a dedicated monument with no `gm_seen`, no
  `gm_ceremony_level` and no `gm_ceremony_pending` is sent to the ceremony as that copy (`gm_state_has_copied_dedication`).
  A landmark sets `gm_ceremony_level`, so it never reads as a copy.
- **`gm_state_first_sight`** writes `gm_seen` and, for a bound dedication (Crown, Republic), `gm_raised_by = owner`, on
  the first refresh after placement. It sets a default skin only when there is none. A landmark therefore needs no
  dedication records of its own; it sets only the landmark records (§3.1).
- **Monuments are recorded on the state**, because buildings hold no variables. `gm_skin` and `gm_form` are each read
  about 150 times. That rules out two monuments in one state (Out of scope).
- **History has no record of 1836 owners in this repository.** The committed `vanilla_parsed/` snapshot leaves out
  `common/history/states`, and no server endpoint answers the question (issue #901). The owners in §2 are checked
  against the game files before implementation.

## 1. What a landmark is

A landmark is an ordinary Grand Monument with five things set:

| Record (state) | Value | Notes |
|---|---|---|
| `gm_landmark` | `flag:<key>` | Marks a landmark and locks it (§3) |
| `gm_skin` | `flag:landmark_<key>` | Its own skin. Gives the name (`gm_skin_landmark_<key>`) and the picture |
| `gm_form` | One form from the roster (§2) | Locked with the skin. Phase 5 reads it for the trophy share |
| `gm_namesake` | `flag:landmark` | A new namesake whose name pattern prints the skin's name (§4) |
| `gm_ceremony_level` | Its level | So it never reads as the engine's copy |

It has the dedication's usual effects and nothing more. v1's rule holds: skins change name, wording and art, never
effects. A landmark takes **no inscription**, since it carries its own historical one. `gm_inscription` keys on
heritage and faith skins only, so this needs no change.

A landmark is **never offered in the style choice** (`monument_events.11`). Phase 4 places landmarks at game start, and
phase 6's commissions, if built, would set them on fulfilment. v1's hook (a `.11` option per landmark, gated on its
state) and the test `test_landmarks_phase_2_hook` are replaced by §7's checks.

## 2. The landmarks

| # | Key | Name | State | Owner | Dedication | Form | Stand-in picture | Level | Raised |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `arc_de_triomphe` | Arc de Triomphe | `STATE_ILE_DE_FRANCE` | FRA | War Memorial | Arch | Generic · Arch | 15 | 1806–36 |
| 2 | `alexander_column` | Alexander Column | `STATE_INGRIA` | RUS | To the Crown | Column | Generic · Column | 10 | 1834 |
| 3 | `brandenburg_gate` | Brandenburg Gate | `STATE_BRANDENBURG` | PRU | To the Nation | Gate | Generic · Gate | 10 | 1791 |
| 4 | `washington_monument_baltimore` | Baltimore's Washington Monument | `STATE_MARYLAND` | USA | To the Republic | Column | Generic · Column | 5 | 1829 |
| 5 | `la_scala` | La Scala | `STATE_LOMBARDY` | AUS (confirmed by the owner) | Grand Opera House | Opera house | Generic · Opera house | 10 | 1778 |
| 6 | `teatro_di_san_carlo` | Teatro di San Carlo | `STATE_CAMPANIA` | SIC | Grand Opera House | Opera house | Generic · Opera house | 5 | 1737 |
| 7 | `jantar_mantar` | Jantar Mantar | `STATE_RAJPUTANA` (Jaipur) | JAI (Dhundhar) | Grand Observatory | Observatory | Sanskrit · Observatory | 5 | 1734 |
| 8 | `shalimar_gardens` | Shalimar Gardens | `STATE_PUNJAB` (Lahore) | PAN | Botanical Gardens | Gardens | Avestan · Gardens | 5 | 1642 |
| 9 | `jardim_botanico` | Jardim Botânico | `STATE_RIO_DE_JANEIRO` | BRZ | Botanical Gardens | Gardens | Generic · Gardens | 5 | 1808 |
| 10 | `stelae_of_aksum` | Stelae of Aksum | `STATE_GONDER` (Aksum's part) | TGR | To the Nation | Stele | Ge'ez · Stele | 5 | 4th century |
| 11 | `liberty_column` | Liberty Column | `STATE_ZEALAND` | DEN | To the Nation | Obelisk | Generic · Obelisk | 5 | 1797 |
| 12 | `lion_monument` | Lion Monument | `STATE_EAST_SWITZERLAND` | SWI | War Memorial | Statue | Generic · Statue | 5 | 1821 |

Picture codes are 1,000,001 to 1,000,012, in this order.

**Added in implementation (owner, 2026-10-11): monuments a revolution contests.** Of the twelve, only the Alexander
Column and the Washington Monument can be contested. The owner asked for more in the countries players most often take
through a political revolution. To the Leader can't serve: it fits only while its honoree rules, so a landmark to a
dead ruler would be contested from the start. These eleven take codes 1,000,013 to 1,000,023:

| # | Key | Name | State | Owner | Dedication | Form | Stand-in picture | Level | Raised |
|---|---|---|---|---|---|---|---|---|---|
| 13 | `temple_of_heaven` | Temple of Heaven | `STATE_BEIJING` | CHI | To the Crown | Hall | Chinese · Hall | 10 | 1420 |
| 14 | `topkapi_palace` | Topkapı Palace | `STATE_EASTERN_THRACE` | TUR | To the Crown | Gate | Arabic · Gate | 10 | 1478 |
| 15 | `golestan_palace` | Golestan Palace | `STATE_IRAKAJEMI` (Tehran) | PER | To the Crown | Hall | Avestan · Hall | 5 | 1806 |
| 16 | `basilica_of_superga` | Basilica of Superga | `STATE_PIEDMONT` | SAR | To the Crown | Mausoleum | Generic · Mausoleum | 5 | 1731 |
| 17 | `tomb_of_william_the_silent` | Tomb of William the Silent | `STATE_HOLLAND` | NET | To the Crown | Mausoleum | Generic · Mausoleum | 5 | 1622 |
| 18 | `cenotaph_of_maximilian` | Cenotaph of Maximilian I | `STATE_TYROL` | AUS | To the Crown | Mausoleum | Generic · Mausoleum | 5 | 1584 |
| 19 | `arco_de_santa_maria` | Arco de Santa María | `STATE_OLD_CASTILE` | SPA | To the Crown | Gate | Generic · Gate | 5 | 1553 |
| 20 | `statue_of_louis_xiv` | Statue of Louis XIV (Lyon) | `STATE_RHONE` | FRA | To the Crown | Statue | Generic · Statue | 5 | 1825 |
| 21 | `lion_of_saint_mark` | Lion of Saint Mark | `STATE_VENETIA` | AUS | To the Republic | Column | Generic · Column | 5 | 12th century |
| 22 | `sans_souci_palace` | Sans-Souci Palace | `STATE_HAITI` | HAI | To the Crown | Hall | Generic · Hall | 5 | 1813 |
| 23 | `nikko_toshogu` | Nikkō Tōshō-gū | `STATE_KANTO` | JAP | To the Crown | Gate | Chinese · Gate | 5 | 1636 |

- The Lion of Saint Mark (a republic's monument in a monarchy) and Sans-Souci (a king's palace in a republic) are
  contested from the first refresh.
- Japan's stays fitting through the Meiji Restoration, which keeps a crown; a republic or conquest contests it.
- Left out: the Vendôme Column (Paris holds the Arc), Prussia's royal monuments (Brandenburg holds the Gate, which stays
  To the Nation), the UK's (London, Edinburgh, Dublin and Calcutta are phase 6's; King William III in Dublin is a live
  sectarian symbol), Belgium (its royal monuments come later) and Egypt (Cairo is the Muhammad Ali Mosque's).

**Baltimore's Washington Monument** is named so (owner, 2026-10-11): players read "the Washington Monument" as the
D.C. obelisk, which Appendix B's commission would also be called.

**Owners checked** against the game's `common/history/states/00_states.txt` (2026-10-11, in implementation): eleven as
guessed. Jaipur's part of Rajputana is Dhundhar's (JAI), not Rajputana's. Aksum is in Tigray's part of `STATE_GONDER`,
and Lahore in Punjab's (PAN) part of `STATE_PUNJAB`.

**How they were picked.**
- **One per state.** None stands in a state that phase 6's candidates (Appendix B) would need.
- **No duplicates.** None is one of the base game's 43 monuments or the mod's 37 wonders.
- **No holy sites.** None sits on a site another faith holds, and none means mainly an atrocity or a live grievance
  today.
- **Every stand-in pair survives the pictures rework.** The three styled civic-progress pairs (Sanskrit observatory,
  Avestan gardens) come from that spec's §2.4.

**What each brings.**
- **Arc de Triomphe:** France's monument to its armies. Inaugurated July 1836.
- **Alexander Column:** contested if Russia's crown falls.
- **Brandenburg Gate:** its Quadriga was carried to Paris in 1806 and back in 1814, the precedent for phase 5.
- **Washington Monument, Baltimore:** the first monument to Washington. Contested if the United States stops being a
  republic.
- **La Scala:** changes hands with Lombardy.
- **Teatro di San Carlo:** the oldest working opera house.
- **Jantar Mantar:** the model for the pictures spec's Sanskrit observatory.
- **Shalimar Gardens:** a Mughal Persian garden, the model for the Avestan gardens.
- **Jardim Botânico:** founded by the Prince Regent in 1808.
- **Stelae of Aksum:** Aksum is the coronation city. Italy took a stele in 1937, and it came back in 2005, the case for
  phase 5.
- **Liberty Column:** commemorates the 1788 reform that ended adscription, which had bound Danish peasants to their
  estates.
- **Lion Monument:** for the Swiss Guards who fell in 1792.

**Dropped in conversation:** Sigismund's Column (Warsaw is Russia's in 1836, and a Russian monument to a Polish king
tells the wrong story).

**Lost to one-per-state:**
- London: Kew, the Crystal Palace, the Albert Memorial and the Cenotaph. London waits for Nelson's Column (phase 6).
- Paris: the July Column, the Opéra Garnier.
- Moscow: the Bolshoi, Minin and Pozharsky.
- St Petersburg: the Bronze Horseman, Pulkovo.
- Berlin: the Victory Column.
- Buenos Aires: the Pirámide de Mayo.

## 3. The lock

### 3.1 Placement

A new on-action, `gm_landmarks_on_game_started_after_lobby`, extends `on_game_started_after_lobby` with the
`on_actions = { … }` form, never `effect`. Behind `gm_system_enabled = yes` and a global `gm_landmarks_seeded` (once
per game), it calls `gm_seed_landmarks`. That effect lives in a new file,
`common/scripted_effects/gm_landmark_effects.txt`, and makes one call per row:

```
gm_seed_landmark = { KEY = arc_de_triomphe STATE = STATE_ILE_DE_FRANCE TAG = FRA DEDICATION = war_memorial FORM = arch LEVEL = 15 }
```

`gm_seed_landmark` does the following:

- In `s:$STATE$.region_state:$TAG$ ?= { … }`, so an owner that proves wrong places nothing and logs a `TE_MONUMENTS:`
  line instead of failing, it runs `create_building = { building = building_grand_monument level = $LEVEL$
  activate_production_methods = { pm_monument_$DEDICATION$ } }`.
- It sets the five records in §1.
- It sets `gm_rebuilding` for one day, the guard Rededicate already uses, so `monument_events.1` (if `create_building`
  fires `on_building_built`) charges no vanity.
- It sends `monument_events.20` to the owner. The refresh then runs `gm_state_first_sight`, which writes `gm_seen` and,
  for a bound dedication, `gm_raised_by`. The journal entry opens through `gm_country_refresh`'s `add_journal_entry`.

A save from before phase 4 gets no landmarks. A debug option places them (§7).

### 3.2 What the lock changes

Two state triggers gate the writers: `gm_state_is_landmark` (`has_variable = gm_landmark`) locks the skin and form, and
`gm_state_has_historical_name` (a landmark whose `gm_namesake` is `landmark`) locks the name.

| Writer | What it does today | For a landmark |
|---|---|---|
| `gm_state_offer_skins` (and `_faith`, `_heritage`) | Sets `gm_skin = generic`, then the default, then `.11` for players | Leaves the skin and asks nothing. It sets `gm_unveil_pending` and sends the refresh, the path a monument with one fitting skin already takes |
| `gm_state_set_default_skin` (first sight) | Sets a skin when there is none | Already a no-op (a landmark has its skin) |
| `gm_state_unveil` | Sets the default form and namesake; for players, `.24` and `.25` | Skips the form and `.24`. Names it as any monument (§3.3) |
| `gm_state_set_default_form` | Sets the skin's default form | Skipped |
| `gm_state_name_if_unnamed` | Names a monument with no namesake | Unchanged (it never sees a named landmark) |
| `gm_rename_sgui` | Reruns `.24` / `.25` | Greyed out while it carries its historical name: "A landmark keeps its historical name". After a rededication renames it, Rename runs `.25` only |
| `gm_name_start_sgui` (Name It, typed names) | Opens the rename popup | Greyed out while it carries its historical name |
| `gm_com_fulfil` | Renames the monument that met a commission (`gm_state_take_commission_name`) | No rename while it carries its historical name. The commission is still met |
| `gm_clear_state`, from `gm_state_rededicate` | Clears every record before the rebuild | Keeps `gm_landmark`, `gm_skin` and `gm_form`. The name goes with the rest |
| `gm_clear_state`, from `gm_state_tear_down` and from demolition (`gm_state_monthly`'s else branch) | Clears every record | Clears them all, `gm_landmark` included: the landmark is gone |

`gm_clear_state` gains a parameter, `KEEP_LANDMARK = yes/no`. Only Rededicate passes `yes`. Every caller passes it
explicitly, which `script_argument_audit` enforces.

### 3.3 Rededication renames it

A rededicated landmark keeps its look but stands for something new, so by default it takes a new name. The building is
rebuilt at half its level, as for any monument, and the ceremony picks a new dedication. Then:

- **The unveiling names it** as it names any newly dedicated monument. The AI takes the city: "The St Petersburg
  Column — To the Republic", still with the Alexander Column's picture. A player gets the namesake choice
  (`monument_events.25`).
- **`.25` gains an option, "Its historical name"**, shown only for a monument on a landmark skin. It sets
  `gm_namesake = landmark` again. A restored crown can put the Alexander Column back.
- The name prints through the form, which the lock keeps: a rededicated Washington Monument is "the Baltimore
  Column".

Only a contested monument can be rededicated, and only bound dedications (Crown, Republic, Revolution, Leader, Shrine)
are contested. Among the twelve, that means the Alexander Column and the Washington Monument.

History has both kinds of case. The Ochterlony Monument in Calcutta became the Shaheed Minar in 1969. The Alexander
Column kept its name under the Soviets, which a player can choose too.

**Undedicated:** a landmark left undedicated by a rededication's ceremony still shows its own picture (§5.1). It has no
namesake, so its name falls back to the skin's: the historical name.

## 4. Its name

- `gm_monument_name_row` and `_evt` gain a `landmark` branch, ahead of the year fallback (`gm_name_year_row`), so a
  landmark never prints a year: `gm_name_landmark_row` = `"[State.GetCustom('gm_skin_name')]"`, and its `_evt` twin
  reads the same through `SCOPE.sState('monument_state')`.
- `gm_skin_name` gains one branch per landmark **ahead of the faith branches**, each printing `gm_skin_landmark_<key>`
  ("Arc de Triomphe").
- The pictures spec makes a civic-progress building show its building's name where a name would fall back to the
  skin's name. The landmark branch comes first, so La Scala prints "La Scala", not "Grand Opera House".
- The journal entry row reads "**La Scala** — Grand Opera House" (`gm_row_title`: the name, then the dedication).
- The state card, ceremony, anniversaries and contest notices name it through the same patterns, so they need no
  change.
- **Loc per landmark:** `gm_skin_landmark_<key>` (its name), plus `gm_landmark_<key>_desc`, one line of history for its
  row tooltip and state card ("Raised 1806–1836 to the armies of the Revolution and the Empire."). Add both to existing
  files, then run `organize_loc.py`.

## 5. Its picture and the AI

### 5.1 The picture

The pictures spec's `gm_state_update_picture` gains one rule, ahead of all the others (including "undedicated → 1"):

- **A landmark shows its own picture** (code 1,000,000 + n) once that picture is in the `PICTURES` table.
- **Until then, it shows its stand-in pair's code.**

The helper's per-landmark branch holds one or the other, and the registry test keeps that in step with `PICTURES`
(§7). The `gm_picture` widget type lists a landmark's own icon only once its picture exists.

Each landmark's picture is drawn in the icon pipeline's `gm_picture` category: `landmark_<key>__<form>.dds` in
`gfx/interface/icons/gm_pictures/`. The pictures spec's rule on archetypes does not apply, because a landmark is the
real monument. None of the twelve is a holy site. The prompts and review sheets belong to the icon session, not to this
spec.

### 5.2 Effects

None of their own (§1).

### 5.3 The AI and a contested landmark

`gm_ai_decide_contests` multiplies **Preserve's weight ×3** for a landmark. Tear Down ends a landmark for good, and
history mostly kept these monuments.

## 6. The civic-progress technologies

The engine switches a building off a method whose unlocking technology its owner lacks (Engine facts). Rajputana in 1836
without Empiricism would lose the Jantar Mantar's dedication, so phase 4 moves the gate out of the methods:

- Remove `unlocking_technologies` from `pm_monument_artistic`, `_naturalist` and `_scientific`. The ceremony's options
  already test the technology (`TECH_GATES` in the registry test), so the ceremony is unchanged.
- The building panel would now offer the three to an undedicated monument without the technology. `gm_state_first_sight`
  catches such a pick: a monument that is not a landmark and stands on one of the three without its technology goes to
  the ceremony, as a copied dedication does. Its options are gated, so the answer replaces the pick.
- A landmark is exempt: it stands on its historical dedication whatever its owner has researched.

Monuments in existing saves are unaffected: each was dedicated with the technology in hand.

## 7. Tests and tools

**`test_grand_monument_registry.py`.** `LANDMARKS` becomes a table of rows: key, state, owner, dedication, form,
stand-in (skin, form), level. It is the checklist for adding a landmark. The test fails unless:

- each row has its `gm_seed_landmark` call, with these values, in `gm_seed_landmarks`;
- each row has its `gm_skin_name` branch ahead of the faith branches, and its loc `gm_skin_landmark_<key>` and
  `gm_landmark_<key>_desc`;
- each form is in `FORMS`, or is the building form of a civic-progress dedication (`BUILDING_FORMS`);
- each stand-in pair has a code in `PICTURES`;
- each code is 1,000,000 + its row number, unique and never reused;
- each landmark has its branch in `gm_state_update_picture`, holding its own code when `PICTURES` lists it and its
  stand-in's code otherwise;
- no two rows share a state;
- no key is a base-game monument or a mod wonder (`bg_monuments` and `building_wonder_*`);
- `monument_events.11` has no landmark option.

**The lock.** One test per row of §3.2:

- each writer has its gate (`gm_state_is_landmark` or `gm_state_has_historical_name`);
- `gm_clear_state` keeps the three records only under `KEEP_LANDMARK = yes`, and only `gm_state_rededicate` passes `yes`;
- `NAMESAKES` gains `landmark`, and `gm_monument_name_row` and `_evt` have its branch ahead of the year fallback;
- `monument_events.25` has the "Its historical name" option, gated on a landmark skin.

**The technologies (§6):** the three methods carry no `unlocking_technologies`, the ceremony's `TECH_GATES` stand, and
`gm_state_first_sight` has the tech check with its landmark exemption.

**Debug** (`te_debug_monuments`):

- An option places every landmark whose state has no Grand Monument and whose owner matches, for testing on a save made
  before phase 4.
- `TE_MONUMENTS:` lines name a landmark's key, level, dedication, status and picture code.

**Audits:** `script_argument` (`gm_seed_landmark`, `gm_clear_state`), `loc_coverage`, `empty_effect`,
`je_immediate_reset` (the seeding writes nothing in a journal entry's `immediate`), `orphaned_event`. Also
`organize_loc.py --check`, `check_gui_lint.py` and the full suite.

**Before implementation:** confirm the twelve owners and Aksum's part of `STATE_GONDER` in the game files, or through
#901 once it's built.

## 8. In-game checks

1. A new game: the twelve stand at their levels, named, with their dedications. Their owners' journal entries are open
   by the first refresh, and no ceremony fires for any of them.
2. With the game rule off in the lobby, none is placed.
3. **The technologies (§6):** La Scala, San Carlo, Jantar Mantar, the Shalimar Gardens and the Jardim Botânico keep
   their dedications in countries without Romanticism or Empiricism. Then, in a country without Romanticism, pick the
   Grand Opera House for an undedicated monument in the building panel: the ceremony opens, with that option greyed.
4. Each shows its stand-in picture (or its own, once drawn) in the row and on the state card.
5. Rename and Name It are greyed out on a landmark with its historical name, with the tooltip.
6. Contest the Alexander Column (playing Russia, `event te_debug_monuments.1`, option c, which contests the tallest
   regime monument). Then:
   - Rededicate: the rebuilt monument keeps its picture under the new dedication, and the namesake choice offers a new
     name or "Its historical name". As the AI, it takes the city's name. Rename works afterwards.
   - Keep as Heritage: it keeps everything.
   - Pull Down: it's gone, and a new monument in Ingria is an ordinary one.
7. A commission met by raising a landmark doesn't rename it.
8. `debug.log` shows no new errors, and no `TE_MONUMENTS:` line reports a landmark that was not placed.

## 9. Player guide

`02-timeline.md` § Grand monuments gets one short paragraph:

- some monuments stand at the start, with a few named as examples;
- a historical monument keeps its look through contest and rededication, and its name unless it is rededicated;
- only Pull Down or demolition ends it;
- Rename is greyed out while it carries its historical name.

The three civic-progress buildings' technologies don't change for players (the ceremony still asks for them), so that
needs no guide edit.

No reference table, which would be more than the guide's peers carry. Rebuild the PDF.

## Out of scope

- **Phase 5 (trophies).** Notes for its spec are in Appendix A.
- **Phase 6 (historical commissions).** Rules and candidates are in Appendix B.
- **Two monuments in one state.** The engine merges one building type's levels in a state into one building, but a
  level-10 building could be counted as two level-5 monuments. The production method isn't the obstacle: it carries only
  the caretaker staff, and every effect is a modifier that script computes, so the dedication could move into a state
  variable and the effects could follow the split. The obstacle is the records. Each monument's skin, form, name,
  status, contest records and picture live on the state under fixed names (`gm_skin` and `gm_form` alone are read about
  150 times), so a second monument needs a second copy of all of them and of every reader. If this is ever wanted, the
  cheaper version is giving the five civic-progress buildings their own building type: they carry fewer records (never
  contested, no honoree, a fixed form), and most capital clashes are a civic-progress building against a political
  monument.
- **Landmarks for old saves**, except through the debug option.
- **The landmark icons themselves**, which belong to the icon session.

## Appendix A: notes for phase 5 (trophies)

Built on 2026-10-12 as `2026-10-12-grand-monument-trophies-design.md`, which fixes the table below form by form.

From the conversation of 2026-10-11:

- **A conqueror can always carry something off, but the share depends on the form**: the whole of a movable object,
  a piece of a structure, a token of a building. The Quadriga, the Elgin Marbles and the horses of San Marco are the
  precedents. A first sketch:

  | What it is | Share of grandeur carried | Forms |
  |---|---|---|
  | A movable object | the whole (v2's half) | Column, Obelisk, Statue, Stele, Pillar, High Cross, Rune Stone, Menorah, Sun Stone, Stela |
  | A piece of a structure | about 25% | Arch, Gate, Tower, Bell Tower, Round Tower |
  | A token | about 10% | Hall, Hall of Fame, Pantheon, Forum, Stoa, Court, Colonnade, Mausoleum, Pyramid, Pagoda, Memorial Church, the civic-progress buildings |
  | Nothing | — | Faith buildings (v1: a conquered shrine becomes heritage) |

- **After a piece is taken, the monument is rebuilt smaller** through Rededicate's ladder, since no effect removes
  levels.
- **A trophy taken from a landmark carries the landmark's records.** The Quadriga is still the Quadriga in Paris.

## Appendix B: phase 6 (historical commissions), if built

**Rules (owner, 2026-10-11):**

- no landmark refers to a person or event after 1836, except an event the game scripts (Victoria's accession);
- no great/major-power gate;
- declining or missing one costs nothing.

**Decided (owner, 2026-10-12):** each is offered once per game, to whoever holds the state, for 40 years, **from the
year its construction began**:

- **The year construction began** (chosen). A commission then takes the player about as long as history took: 5 to
  10 years for 5 or 10 levels. The monument stands about when the real one did.
- **The year it was completed** (v2 §7's choice for most; not chosen). The monument then stands 5 to 10 years after the real one:
  Walhalla around 1850 instead of 1842.

**Candidates that pass the rules** (state, dedication, skin · form, target). O'Connell Tower is borderline: O'Connell
is a figure from before 1836, but the tower marks his death in 1847.

| Landmark | From | State | Dedication | Skin · form | Target |
|---|---|---|---|---|---|
| Walhalla | 1836 | `STATE_BAVARIA` | To the Nation | Gothic · Hall of Fame | 5 |
| Bunker Hill Monument | 1836 | `STATE_MASSACHUSETTS` | War Memorial | Generic · Obelisk | 5 |
| Obelisk of the Second of May | 1836 | `STATE_NEW_CASTILE` | War Memorial | Generic · Obelisk | 5 |
| Muhammad Ali Mosque | 1836 | `STATE_LOWER_EGYPT` | Grand Shrine | Sunni · Great Mosque | 10 |
| Hermannsdenkmal | 1838 | Lippe's state (Westphalia or Hanover) | To the Nation | Generic · Statue | 5 |
| Nelson's Column | 1840 | `STATE_HOME_COUNTIES` | War Memorial | Generic · Column | 5 |
| Scott Monument | 1840 | `STATE_LOWLANDS` | To the Nation | Gothic · Tower | 5 |
| Washington Monument | 1848 | `STATE_DISTRICT_OF_COLUMBIA` | To the Republic | Generic · Obelisk | 10 |
| O'Connell Tower | 1855 | `STATE_LEINSTER` | To the Nation | Irish · Round Tower | 5 |
| Millennium of Russia | 1859 | `STATE_NOVGOROD` | To the Nation | Generic · Statue | 5 |
| Vienna Court Opera | 1861 | `STATE_AUSTRIA` | Grand Opera House | Generic | 5 |
| Panathenaic Stadium | 1869 | `STATE_ATTICA` | Grand Stadium | Greek | 5 |
| National Pantheon, Caracas | 1874 | `STATE_MIRANDA` | To the Nation | Generic · Hall | 5 |
| Royal Exhibition Building | 1879 | `STATE_VICTORIA` | Great Exhibition Hall | Generic | 5 |
| Teatro Colón | 1889 | `STATE_BUENOS_AIRES` | Grand Opera House | Generic | 5 |
| Palace of Fine Arts, Chicago | 1891 | `STATE_ILLINOIS` | Great Exhibition Hall | Generic | 5 |
| Millennium Monument | 1896 | `STATE_CENTRAL_HUNGARY` | To the Nation | Generic · Column | 5 |
| Völkerschlachtdenkmal | 1898 | `STATE_SAXONY` | War Memorial | Gothic · Tower | 10 |
| Angel of Independence | 1902 | `STATE_MEXICO` | To the Nation | Generic · Column | 5 |
| Victoria Memorial | 1906 | `STATE_WEST_BENGAL` | To the Crown | Generic · Hall | 10 |
| Estadio Centenario | 1929 | `STATE_URUGUAY` | Grand Stadium | Generic | 5 |
| Palomar Observatory | 1936 | `STATE_CALIFORNIA` | Grand Observatory | Generic | 5 |
| Gateway Arch | 1963 | `STATE_MISSOURI` | To the Nation | Generic · Arch | 10 |

Some need a holder condition (a German, Russian, Hungarian or Greek primary culture for the national ones; crowned for
the Victoria Memorial; a republic for the Washington Monument). The Muhammad Ali Mosque needs a Sunni state religion.
Muhammad Ali himself ruled in 1836.

**Ruled out by the rules:** Lenin's Mausoleum, Ho Chi Minh's Mausoleum, the Sun Yat-sen Mausoleum, Anıtkabir, the
Monument to the People's Heroes, the Motherland Calls, India Gate, the Rizal Monument, Lima's Dos de Mayo, Seoul's
Independence Gate, Monas, Accra's Independence Arch and the Vittoriano.

**Left out on purpose:**
- Mount Rushmore: the Black Hills are sacred to the Lakota.
- The Voortrekker Monument and Stone Mountain: what they stand for.
- Holocaust memorials: no game object should profit from one.
- The Valley of the Fallen and Yasukuni (v2).
