# Grand Monuments: ageing, the freeze and building beside, play-test checklist

What the next play-test should look at for the ageing rework (spec
`docs/superpowers/specs/2026-10-16-grand-monument-ageing-design.md`, plan
`docs/superpowers/plans/2026-10-16-grand-monument-ageing.md`). In-game checks do not gate a merge (CLAUDE.md, "In-game
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
| `TE_SELF_CHECK OK/BROKEN monument_rebuild_ungated` | The first Grand Monument a script rebuilt (a return, a piece taken, a promotion, Rededicate) stands at the level it asked for, a pulse later. | `create_building` refuses or changes a rebuild even with the expansion gate held open (`gm_state_can_expand` passes while `gm_rebuilding` stands). Read the line's two numbers: no building means the rebuild failed outright; raise a global flag around each rebuild as `te_cm_placing_site` does and accept it in `can_build_government` too. |
| `TE_SELF_CHECK OK/BROKEN monument_merge_kept` | The first time a game settles a monument whose state merged into another part of its region (issue #936) and which was not a revolt's split piece (the next row): OK when its shadow was adopted, as the state's own monument or beside the one there, because a building in the region held levels its records lacked; BROKEN when none did. The line prints the levels recorded, the most levels found unaccounted for and the buildings standing in the region. **Read 2026-10-17** (1836 observer run, build `5e369c73`): BROKEN with 1 building, twice, both a revolt's split piece coming home, which the probe could not tell from a separate monument: Tuscany's Proletarian Revolt (1876–77, Uffizi Gallery, a 2-level piece) and the Paris Commune (1886–87, Arc de Triomphe, a 4-level piece; in 1898 the Arc still stood at 11 levels on records of 15). Those now take the next row's path; no genuine merge has been read yet. The same save shows a building moving whole into a part with none: the Stelae of Aksum's 1836 building object stands in Gonder's surviving state under the records of a monument first named in 1866, a merge the path never logged (its shadow missing, or never read as an orphan; not established). | BROKEN with no building in the region: the absorbed part's building does not survive a merge, so nothing can be adopted; the records could only be rebuilt (`gm_state_tr_rebuild_from_moving` from the shadow in the most populous state of the region), which costs a rebuild on a pulse. BROKEN with buildings standing: first check the region had no revolt in the months before (a piece whose monument kept all its levels through the split still reads as lost); if not, the absorbed building's levels do not join the survivor's (it keeps its own), so adopt the shadow beside with no levels check and add its levels to the building through `gm_state_tr_add_levels`. Note which part survived (read 1 below) either way. Read from that run's 1898 save (state ids against the 1836 history's order): in Tuscany and Paris the old government's state object survived; in Delhi (the Company annexing the Mughals, 1861) the annexed Mughal part's did, and the Company's own went. |
| `TE_SELF_CHECK OK/BROKEN monument_split_rejoined` | The first time a game settles a revolt's split piece coming home (`gm_sh_rejoin`): an orphan no building takes, in a region whose recorded monument lacked levels when its shadow was last written (`gm_sh_short`; a revolt that takes part of a state gives the new part's building a share of the levels, and the refresh records that share as a new monument). Its levels go back on the monument's building, no more than it lacks now, by one rebuild; the piece goes. OK when the piece held no more levels than the monument lacked (the split took them from it); BROKEN when it held more. The line prints the piece's levels, what the monument lacked when last seen and lacks now (the difference came back with the merge), and what was put back. | BROKEN: the piece grew during the split (the rebels built on it), and those levels are lost; stand the excess beside the monument as its own (`gm_sh_adopt_beside` on a copy with the excess, plus `gm_state_tr_add_levels`). OK but the card's levels still fall short a day later: the rebuild did not come back (read `monument_rebuild_ungated`). |

## Ageing

| Check | Expect | If it fails |
|---|---|---|
| **A year on.** Note the Arc de Triomphe's Grandeur on Paris's state card, then wait a year. | Its Grandeur rises by about 0.3 (15 levels × 2%), and its Finished line shows Age +0.3. | No change: `gm_state_ages` fails for it (dedicated, `gm_seen`, not contested). |
| **A contested one does not age.** Watch the Lion of Saint Mark in Venice. | Its age stays at 0 while it is contested. | |
| **Mothballed.** Switch to Mothballed for a year. | Ageing halves. | |
| **A trophy abroad.** The Luxor Obelisk in Paris. | Its worth on the Trophies row stays the same from year to year. | |

## The freeze and building beside

| Check | Expect | If it fails |
|---|---|---|
| **Queued levels join it.** Build a new monument with five levels queued at once. | The ceremony asks at the first level; dedicate it. The other four join it, and its Finished line appears once the last is done, at 5 levels. | Finished at 1: `gm_state_record_frozen_levels` did not wait for `is_under_construction`. Queued levels cancelled or stalled while the ceremony asked: the gate closed on a monument still being built (it should hold only a finished one, `has_variable = gm_levels`). |
| **Building beside.** Queue three more levels on that finished monument. | When the first finishes, the old monument moves to Also Standing Here with its name, picture and dedication, and a new draped monument stands first and is asked its dedication. The other two levels join the new one. | The old one lost its name or dedication: a record missed `gm_state_demote_primary`. |
| **The grandest stands first.** Name the new one. | Within a month the older, grander monument is the state's own again and the new one stands beside it, each with its own dedication. | |
| **Both dedications count.** A crown monument beside a civic one. | Legitimacy counts the crown's grandeur, Petty Bourgeoisie approval the civic one's; the local effects show both dedications in the state's modifiers. | |
| **The gate.** Try to expand a contested monument, and one in a state where six already stand. | The build button is greyed with the reason. | It builds anyway: `can_build_government` does not gate expansion. New levels on a contested monument still found a monument beside it (the contest moves with the old one). Note it; the gate is UX only. |
| **The AI.** Watch an AI country with a monument for a decade. | It builds new monuments in other states before it builds beside one. | |

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
| **Into a monument.** Before the annexation, build and dedicate a monument in the Company's part of Delhi, and let its construction finish. | The Red Fort stands beside it after the merge, and the building's level is the sum of both. If the Red Fort is grander, it does not swap in: only a newcomer settles that way. | The building at the Company's level only: levels do not add (BROKEN); the Red Fort is lost. |
| **Colonization.** Colonize the last province of a decentralized nation's part of a state that a landmark stands in (Great Zimbabwe, `STATE_ZAMBEZI`, Mashona). | The same adoption as a merge, if the building comes along. | Nothing adopted: note what happened to the part's building. |
| **A revolt's piece comes home.** As France, let the Paris Commune rise (it takes one province of Île-de-France), or as a one-state country (Tuscany) lose part of the state to a revolution; note the monument's levels on the state card before, during and after. | During the revolt the monument's building holds fewer levels than before, and the rebels' part shows a new monument with the rest (a ceremony may ask them). Within a month of the revolt's end a `TE_MONUMENTS: ... was a piece a revolt split from the monument there, and rejoins it` line, the self-check `monument_split_rejoined` logs OK, and the card shows the monument at its old levels, with nothing new beside it. | A `... is lost` line instead: the monument lacked nothing when last seen (the split copied levels rather than taking them; note the levels during the revolt). A monument beside it after the revolt (`gm_sh_adopt_beside`): the merge brought the piece's levels back but the survivor's records did not count them. The card short of the old levels a day later: the rebuild did not come back (`monument_rebuild_ungated`). |
| **A revolt that wins.** A revolt that takes part of a monument's state and wins (Dahomey's Abolitionist Revolt took the Royal Palaces of Abomey's state in 1874). | The winner's part is the survivor: the old monument stands beside the piece the refresh recorded, or as the state's own. | In the 2026-10-17 run nothing was adopted: a week after the revolt won, the winner's building stood at 5 levels on its piece's 4, and the extra level founded a new monument beside (`TE_MONUMENTS: new levels founded a monument beside`); the Abomey's records were gone by 1898. Note whether a `TE_MONUMENTS:` merge line appears at all. |
| **No loss in ordinary play.** A monument whose state changes hands whole (no other part held by the new owner). | Nothing changes: the state survives, and its shadow is refreshed in place. | |

## Secondaries' contests

| Check | Expect | If it fails |
|---|---|---|
| **A contested secondary.** Have a crown monument stand beside another, then change to a republic. | Its row in Our Monuments shows Contested with Pull Down, Rededicate and Keep as Heritage; the contest notice lists it. | |
| **Pull Down two at once.** Use Tear Them All Down on the notice with two contested secondaries in one state. | Both go, and the building ends at its level less their levels together: in one shrink if the queued `.30` events run after the option, or a day apart if each runs at once. | A building at the wrong level: a second shrink read the first one's stale level. |
| **Tear them all down, the first one too.** A contested primary with a grander contested secondary beside it, both on one notice, and a third, uncontested monument beside them. Use Tear Them All Down. | Both contested ones go. The uncontested one stands first, with its own name and dedication, in a building at its own levels. With no third monument the building is gone. | The grander contested one stands first, still contested: `gm_state_pull_down_ordered` did not see its order (the order was not set before the primary's pull-down, or the filter failed). |
| **A row's Pull Down, then the first one.** With a contested secondary beside a contested primary, click Pull Down on the secondary's row, then at once pull down the primary from its own row. | Both go; the building is gone, or stands at what else remains. | The secondary stands first: as above. |
| **Rededicate a secondary.** | It becomes the state's own monument at half its levels and half its age, asked its dedication; the old first one stands beside it. | |

## Opportunities and events

| Check | Expect | If it fails |
|---|---|---|
| **Progress counts levels.** Seize an opportunity, then wait without building. | Progress does not move with ageing. Building a new monument, or levels beside a finished one, moves it. | |
| **The gift.** Complete one. | The completing monument gains +5 Grandeur, no rebuild (its staff stay). | |
| **A completion doesn't crash.** Load `crash_2026-10-17_china_opportunity.v3` (the 1898 observer autosave both 2026-10-17 crashes came from; China's opportunity completes within a month), or complete any opportunity whose monument is dedicated. | The game runs on; the monument gains +5 Grandeur once, and the group's approval and the boon come once. | An `EXCEPTION_STACK_OVERFLOW` dump in `crashes/`: something in `gm_com_fulfil` before `gm_com_close` fires a refresh again (`monument_events.20`), and the refresh seizes the still-open opportunity a second time. |
| **An anniversary.** Take an anniversary's first option. | The monument gains a tenth of its levels as grandeur, at least 1, and the option's tooltip says so. | |
| **An anniversary beside another.** A crown monument standing beside a grander civic one. | The Jubilee comes for it; its text reads "the monument standing beside <the first one> in <state>", and its first option adds to the crown monument's age, not the first one's. | The first one's age rose: `gm_ann_add_age` read `monument_state`. |
