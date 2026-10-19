# Grand Monuments: ageing, construction sites and recorded size, play-test checklist

What the next play-test should look at for the ageing rework (spec
`docs/superpowers/specs/2026-10-16-grand-monument-ageing-design.md`, plan
`docs/superpowers/plans/2026-10-16-grand-monument-ageing.md`) and for construction sites with the size in records (spec
`docs/superpowers/specs/2026-10-18-grand-monument-sites-and-world-wealth-design.md`, plan
`docs/superpowers/plans/2026-10-18-grand-monument-sites-plan-a.md`). In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): the PR lands on the offline gate and this is what only the game can show.
A fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work".
- **Start a game in 1836** with the Grand Monuments rule on, as France (the Arc de Triomphe in Paris, the Lion of Saint
  Mark contested in Austrian Venice for comparison) or any country with a landmark.
- **Logs.** Read `debug.log`; grep `TE_SELF_CHECK` and `TE_MONUMENTS`.
- **Console.** `event te_debug_monuments.1` and the debug events of the other play-test lists.

## Self-checks

| Line | Means | If BROKEN, take the fallback |
|---|---|---|
| `TE_SELF_CHECK OK/BROKEN monument_created_on_dedication` | The first restore after a construction site's dedication made its finished building: OK when `create_building`'s `activate_production_methods` put the dedication on it; BROKEN when the engine's copy won and `gm_restore_pm` had to switch it. | Nothing to do for play: the restore is the fallback. If it is BROKEN, the switch is a second one in the building's first days; drop `activate_production_methods` from `gm_state_finish_site` and rely on the restore alone. |
| `TE_SELF_CHECK OK/BROKEN monument_migrated` | Once a game, a month after an older save's dedicated monument was migrated (`monument_events.32`: records written, building reset to level 1), its grandeur is within 1% below and 5% above what it was. | BROKEN: the records missed its size (`gm_levels` from the old arithmetic) or a reader still reads the building's level; compare its state card with the save before loading. |
| `TE_SELF_CHECK OK/BROKEN gm_world_base` | Once, on a new game's first pass (before 1836.3.1): world GDP is within a tenth of the 1836 constant the world-wealth rate is measured against (`gm_world_gdp_1836`, 334,000,000). | Set `gm_world_gdp_1836` to the figure the line prints. |
| `TE_SELF_CHECK OK/BROKEN monument_merge_kept` | The first time a game settles a monument whose state merged into another part of its region (issue #936): OK when its shadow was adopted (onto a building nothing recorded, beside the monument there, or raised into a new one); BROKEN when no part of its region took it. | Lost: note which state survived the merge and who owned it; the orphan looks for its last owner's part (`gm_sh_owner`). |
| `TE_SELF_CHECK OK/BROKEN monument_merge_level1` | Once a game, a day or more after a merge's reset (`gm_state_reset_building_level`), with its dedication recorded: OK when the merged region's finished building stands at level 1 on the dedication its records name; the line prints the level the merge left it at. | Note that level and the method it stood on; if the merge kept the other part's method, `gm_restore_pm` from `gm_dedication` should have put it back, so a BROKEN here means the restore did not run. |

## Ageing

| Check | Expect | If it fails |
|---|---|---|
| **A year on.** Note the Arc de Triomphe's Grandeur on Paris's state card, then wait a year. | Its Grandeur rises by about 0.3 (15 levels × 2%), and its Finished line shows Age +0.3. | No change: `gm_state_ages` fails for it (dedicated, `gm_seen`, not contested). |
| **A contested one does not age.** Watch the Lion of Saint Mark in Venice. | Its age stays at 0 while it is contested. | |
| **Mothballed.** Switch to Mothballed for a year. | Ageing halves. | |
| **A trophy abroad.** The Luxor Obelisk in Paris. | Its worth on the Trophies row stays the same from year to year. | |

## Construction sites (sites plan A)

| Check | Expect | If it fails |
|---|---|---|
| **Build a site.** As a player, build a Grand Monument in a state with none. | The build menu offers *Grand Monument (Under Construction)*; the state view shows its own card under the tourism card (levels built, grandeur so far, "Levels are still being built here"), and the tab's Awaiting Dedication lists it. No upkeep shows on it. | No card: `gm_state_disp_site`. |
| **Pause and resume.** Queue five, cancel two before they finish, let the rest finish. | Dedicate is greyed while any is queued and enables once none is; the card reads 3 levels and 3 grandeur within a month. | |
| **Dedicate it.** Press Dedicate and pick a dedication. | The site goes; a Grand Monument stands at level 1 in the building list, on that dedication; its card shows Finished: 3 levels; it sits under Our Monuments. Within a month its upkeep is 0.3 construction (0.45 Open, none Mothballed). | Not on its dedication after a month: the restore failed (see `monument_created_on_dedication`). Upkeep 0.1: `gm_upkeep`'s multiplier did not resolve. |
| **Build beside it.** Build another site in that state and dedicate it. | The new monument stands first until it is named; then the grander one stands first and the other beside it, each on its own dedication. The building stays at level 1. | |
| **The gate.** Try to start a site where the monument is contested, and where six monuments (sites counted) stand. | The build button is greyed with the reason. | It builds anyway: `can_build_government` does not gate it. |
| **A lost building.** Strike a state with a finished monument with a nuclear weapon, or remove its building with the console. | Within a month the building is back at level 1 on its dedication; the monument's levels and grandeur are unchanged. | Gone for good: `gm_state_lost_building` (needs `gm_migrated`, `gm_dedication`). |
| **The AI.** Watch an AI country with a monument for a decade. | It builds sites in other states before it builds beside one, and dedicates each once nothing more is queued. It never downsizes a site (`downsizeable = yes`). | It downsizes sites: the engine's AI treats a site as an unprofitable building; set `downsizeable = no` on `building_grand_monument_site`. |
| **An older save.** Load a save from before construction sites with a dedicated monument of 15 levels, an undedicated one, and one with levels queued. | Within a month: the dedicated one's building is at level 1 with its grandeur unchanged (`monument_migrated`); the undedicated one is a site at its levels with a Dedicate button; the queued one waits until its levels finish, then migrates: a dedicated one with levels queued on it ends at its recorded size, and the levels above it stand as a site with a Dedicate button. | The dedicated one with queued levels lost them: `gm_mig_excess` read after the reset. |

## World wealth (sites plan B)

| Check | Expect | If it fails |
|---|---|---|
| **The rate in three places.** In 1836, open National Effects, a site's card, and the build menu's Grand Monument (Under Construction) tooltip. | Each says a level finished now adds about 1.000 grandeur. In a late save (2000 on), a few thousandths, with the levels that make one; National Effects' hover says how many times richer the world is. | The build tooltip shows no line: the build menu does not render `possible` custom tooltips that pass; the card and the panel still show it. |
| **A site across January.** Build levels on a site in December and January of a late save. | The site's grandeur grows by the December rate for December's levels and the new rate for January's. | |
| **A late opportunity.** Seize one in a late save and press Raise It. | It queues many more than 5 levels (at most 100), and its cost line says so. Completing it needs the grandeur, not the levels. | Raise It queues 5: `gm_com_levels_to_go` ignored the rate. |
| **Vanity in hard times.** Finish levels in a late save during a recession. | The legitimacy hit is the grandeur they add, a fraction of a point a level. | No hit at all, radicals only: the ledger read `$AMOUNT$` on the country. |
| **The AI tops up.** Watch an AI country seize an opportunity in a save past 1950 (observer). | It queues at most 100 levels, dedicates the site, then queues what is still missing until the opportunity is met or runs out. | It stops after the first site: `gm_com_monthly`'s top-up did not run. |
| **Rededicate beside.** Rededicate a contested monument that stands beside another. | The ceremony asks; dedicated, it stands first at half its levels. | It stands first but nothing asks: `gm_state_start_ceremony` refused while the swap's restore stood. |

## A merged state (issue #936)

Every check reads `TE_MONUMENTS:` and `TE_SELF_CHECK` lines in `debug.log`; note the state card and Our Monuments before
and after. The probe answers the issue's five reads: which state survives the merge (the acquirer's part, the larger part,
or a new state); whether the absorbed part's variables are lost; whether its `building_grand_monument` moves into the
merged state and whether its levels add to a monument already there; whether `on_state_owner_change` fires for the
absorbed part, and before or after the merge; and what colonizing a decentralized nation's last province does.

| Check | Expect | If it fails |
|---|---|---|
| **The Red Fort.** As the East India Company, annex the Mughals (`MUG`, one province of Delhi) and wait a month. | Within the month the Red Fort stands again in the Company's Delhi, with its name, picture, landmark line and age: as the state's own monument if the Company's part had none, or beside the one there. A `TE_MONUMENTS:` line says which, and the self-check logs OK. It is contested (the Company did not raise it), as any conquered monument. | A `TE_MONUMENTS: ... is lost` line and BROKEN: read its numbers against the Self-checks row. A dedication ceremony for the Red Fort, or a draped "new monument" beside: the adoption ran after something read the building (`gm_state_merge_pending` missed it). |
| **The Jantar Mantar.** As Jodhpur, take Jaipur's part of Rajputana (`JAI`) in a war. | As above, in Jodhpur's Rajputana, but not contested: a scientific monument honours no order. | As above. |
| **Into a monument.** Before the annexation, build and dedicate a monument in the Company's part of Delhi, and let its construction finish. | The Red Fort stands beside it after the merge, and the building stands at level 1. If the Red Fort is grander, it does not swap in: only a newcomer settles that way. | The building at the Company's level only: levels do not add (BROKEN); the Red Fort is lost. |
| **Colonization.** Colonize the last province of a decentralized nation's part of a state that a landmark stands in (Great Zimbabwe, `STATE_ZAMBEZI`, Mashona). | The same adoption as a merge, if the building comes along. | Nothing adopted: note what happened to the part's building. |
| **A revolt keeps the monument whole.** As France, let the Paris Commune rise (it takes one province of Île-de-France), or lose part of a monument's state to any revolt. | The Arc de Triomphe stays whole in France's part, its levels and grandeur unchanged; the rebels' part has no Grand Monument (`TE_MONUMENTS: a Grand Monument building no record describes ... is removed` if the engine copied the building there). When the parts merge again, nothing changes. | The monument appears in the rebels' part too: `gm_state_stray_building` did not hold (an orphan in the region, or a mark it should not have). |
| **No loss in ordinary play.** A monument whose state changes hands whole (no other part held by the new owner). | Nothing changes: the state survives, and its shadow is refreshed in place. | |

## Dedicate (owner, 2026-10-18)

| Check | Expect | If it fails |
|---|---|---|
| **No ceremony at the first level.** As a player, build a site with five levels queued. | No ceremony when the first level finishes; the button is greyed until the last. | A ceremony opens: a path other than the button started it (`DedicateButtonTests` lists the allowed ones). |
| **Not yet.** Press Dedicate and pick "Let it stand as it is, for now". | The button is back at once; nothing else changes. | Greyed for 30 days: the option did not clear `gm_ceremony_pending`. |
| **Rededicate asks first.** Rededicate a contested monument, then pick "Keep it as it is". | Nothing is paid and nothing changes. Rededicate again and dedicate: it costs 500 a level, and the monument keeps half its levels, grandeur and years, on the new dedication. | Paid on the press: `gm_state_rededicate` charged before the answer. |
| **The AI still finishes its monuments.** Watch an AI great power raise a monument (observer). | Its ceremony comes once its site's levels are done, and its monument stands dedicated within a month. | AI sites stay for years: `gm_state_ai_dedicates_now`. |
| **An old save's open ceremony.** Load a save whose ceremony is open. | The ceremony still answers; the monument migrates once it is closed. | |
| **The chain opens as windows (owner, 2026-10-19).** As a player with a finished site, press Dedicate, pick a dedication with more than one style, then a form and a name. | Each of the ceremony, the style, the form and the name opens as a window the moment the last one is answered, with no card to click in the notification list in between. (Landmarks and single-style dedications skip the style, or the form, as before.) | A small card waits in the notification list instead: `popup = yes` does not take from a state scope (these are the mod's only state events that ask for it), or `is_popup` is ignored. Try dropping the other of the two on `monument_events.2`; if one switch alone does it, remove the redundant one from the chain and update `DedicationPopupTests`. |
| **Anniversaries stay cards.** Wait for a monument anniversary. | A card in the notification list, as before. | A window: `is_popup` leaked onto an anniversary event. |

## Secondaries' contests

| Check | Expect | If it fails |
|---|---|---|
| **A contested secondary.** Have a crown monument stand beside another, then change to a republic. | Its row in Our Monuments shows Contested with Pull Down, Rededicate and Keep as Heritage; the contest notice lists it. | |
| **Pull Down two at once.** Use Tear Them All Down on the notice with two contested secondaries in one state. | Both go with their records; the building stays at level 1 for what remains. | |
| **Tear them all down, the first one too.** A contested primary with a grander contested secondary beside it, both on one notice, and a third, uncontested monument beside them. Use Tear Them All Down. | Both contested ones go. The uncontested one stands first, with its own name and dedication, in a building at its own levels. With no third monument the building is gone. | The grander contested one stands first, still contested: `gm_state_pull_down_ordered` did not see its order (the order was not set before the primary's pull-down, or the filter failed). |
| **A row's Pull Down, then the first one.** With a contested secondary beside a contested primary, click Pull Down on the secondary's row, then at once pull down the primary from its own row. | Both go; the building is gone, or stands at what else remains. | The secondary stands first: as above. |
| **Rededicate a secondary.** | It becomes the state's own monument and is asked its dedication; dedicated, it keeps half its levels and half its age; the old first one stands beside it. | |

## Opportunities and events

| Check | Expect | If it fails |
|---|---|---|
| **Progress counts levels.** Seize an opportunity, then wait without building. | Progress does not move with ageing. A site's levels count once it is dedicated. | |
| **The gift.** Complete one. | The completing monument gains +5 Grandeur, no rebuild (its staff stay). | |
| **A completion doesn't crash.** Load `crash_2026-10-17_china_opportunity.v3` (the 1898 observer autosave both 2026-10-17 crashes came from; China's opportunity completes within a month), or complete any opportunity whose monument is dedicated. | The game runs on; the monument gains +5 Grandeur once, and the group's approval and the boon come once. | An `EXCEPTION_STACK_OVERFLOW` dump in `crashes/`: something in `gm_com_fulfil` before `gm_com_close` fires a refresh again (`monument_events.20`), and the refresh seizes the still-open opportunity a second time. |
| **An anniversary.** Take an anniversary's first option. | The monument gains a tenth of its levels as grandeur, at least 1, and the option's tooltip says so. | |
| **An anniversary beside another.** A crown monument standing beside a grander civic one. | The Jubilee comes for it; its text reads "the monument standing beside <the first one> in <state>", and its first option adds to the crown monument's age, not the first one's. | The first one's age rose: `gm_ann_add_age` read `monument_state`. |
