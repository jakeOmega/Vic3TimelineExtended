# Grand Monuments: several monuments in one state, play-test checklist

What the next play-test should look at for monuments that share a state (spec
`docs/superpowers/archive/specs/2026-10-13-multiple-monuments-per-state-design.md`, plan
`docs/superpowers/archive/plans/2026-10-13-multiple-monuments-per-state.md`). In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): the PR landed on the offline gate and this is what only the game
can show. A fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Start a game in 1836** with the Grand Monuments rule on. France holds the Luxor Obelisk and the Dendera Zodiac, which
  are Upper Egypt's; the Obelisks of Karnak stand there already.
- **Logs.** Read `debug.log`, not `error.log`; grep `TE_SELF_CHECK` and `TE_MONUMENTS`.
- **Console.** `event te_debug_monuments.5` seeds the landmarks and trophies again (option c), `.6` is the trophy debug.
  Vic3 has no `effect` command.

## Self-checks

Logged once at the start of a game, after the seeding. Nothing logged means the premise was absent (the monument did not
stand, the owner proved wrong, or the system is off).

| Line | Means | If BROKEN, take the fallback |
|---|---|---|
| `TE_SELF_CHECK OK/BROKEN monument_piece_rejoins` | A trophy that is a piece of the standing monument (the Parthenon's marbles in Attica) reads as one, so it will rejoin it. | The cross-scope flag comparison in `gm_state_stands_for_moving` (`var:gm_landmark = scope:gm_tr_moving.var:gm_tr_landmark`) does not hold. Stage the trophy's landmark on the origin state first with `set_variable = { name = gm_tr_ret_landmark value = scope:gm_tr_moving.var:gm_tr_landmark }` (the cross-scope read `gm_tr_copy_to_state` proves) and compare same-scope, `var:gm_landmark = var:gm_tr_ret_landmark` (as `te_tax_display_values.txt` compares two variables). Do the same for the secondaries in `gm_tr_rejoins_secondary`. |
| `TE_SELF_CHECK OK/BROKEN monument_artifact_stands_apart` | A returned artifact with a monument already standing (the Luxor Obelisk in Upper Egypt) reads as apart from it, so it will stand beside it. | The same comparison, read the other way: with both BROKEN the comparison is always false or always true. |
| `TE_SELF_CHECK OK/BROKEN gm_occupation_read` | Logged at the first monthly pass, in a save already under way too (log triage, 2026-10-16). A monument state whose owner is at peace counts its provinces (at least one) and finds its owner holding half of them, so the trophies' occupation read works: `gm_state_tr_holds_half`, a script value's `every_province` with a saved country. Before, `random_province` ran from the state, which the engine rejects, and no occupier was ever found. | Counts no provinces: read the state's own `controller` link (`controller = $WHO$` in `gm_state_tr_occupied_by`, `controller ?= { save_scope_as = gm_tr_occupier }` in `gm_state_tr_find_occupier`), whatever it returns under partial occupation. Counts them but the owner holds under half: the script value can't see the temporary scope, so store the country on the state first (`set_variable = { name = gm_tr_who value = <country> }` in the effects, compared with `var:gm_tr_who`) and drop the trigger form, which the Carry It Off buttons read from a scripted GUI. |

## Returns

| Check | Expect | If it fails |
|---|---|---|
| **Luxor Obelisk home.** As Egypt (or any owner of Upper Egypt), get the Luxor Obelisk returned (Return Cultural Property, or take it from France in a war). | Upper Egypt keeps the Obelisks of Karnak as the state's monument and gains the Luxor Obelisk beside it. The state's building is 5 levels taller, on the same dedication, and the monument card lists the Obelisk with its own picture and name under Karnak's details. The Homecoming runs. | The card missing with the building taller: the monthly pass did not list it (`gm_monuments_here`). The Obelisk merged into Karnak: read the self-check. |
| **Both home.** Return the Dendera Zodiac too. | Two rows on the card; the building stays at level 1, and the three monuments' levels are their own (Karnak 10, Luxor 5, the Zodiac 2). Karnak's own grandeur on the state card's Grandeur hover reads 50. | Karnak's grandeur changes: a return wrote the wrong records. |
| **Both home in one treaty** (review 2026-10-16; records since sites plan A). Enforce Return Cultural Property on France with both trophies still in Paris. | Both come home at once and stand beside Karnak; the building stays at level 1. | One trophy never coming home: note what the return logged. |
| ~~**An undedicated primary**~~ Retired by sites plan A: every finished monument carries a dedication; a monument still being built is a site. | | |
| **A piece rejoins.** Return the Parthenon's marbles to Attica. | The levels go on the Parthenon; no new row. The Piraeus Lion returned there stands beside it as a row. | The marbles as a row of their own: self-check. |
| **Dedication kept.** Return a civic artifact to a state whose monument is Crown. | The building keeps Crown; legitimacy from regime grandeur does not rise by the artifact's levels; prestige does. | Crown legitimacy rising: a dedication sum still reads `gm_state_grandeur`. |

## Trophy pictures (2026-10-16, #972)

A landmark's trophy shows its own picture, what was carried off on display in a museum room, drawn over its monument's
picture by a widget type that instances `gm_tr_picture` and puts more icons over it (`gm_tr_trophy_picture`). No mod
GUI has stacked a type's icons over another type inside one widget before, so this is the check that proves it.

| Check | Expect | If it fails |
|---|---|---|
| **On display.** As Britain in 1836, open the Home Counties' Trophies on Display, and the journal entry's Trophies section, a month in. | The Marbles row shows the marbles in a skylit room, the Rosetta Stone in its room, Tipu's Tiger in its case; Paris's rows the Luxor Obelisk in a glass-roofed court. Before the first month's pass: the monument's picture. | The monument's picture after a month: `gm_tr_picture_trophies` did not set a code (`gm_tr_trophy_picture_code`). Nothing at all, or the monument's picture over the trophy's: the overlay type doesn't draw as stacked; fall back to `gm_tr_picture = {}` in the three trophy rows (the data stays, the trophy pictures go unused). |
| **Held Abroad.** As Greece, open Held Abroad. | The Marbles and the Piraeus Lion rows show their trophy pictures. | As above. |
| **Home again.** Return the Luxor Obelisk to Upper Egypt (it stands beside Karnak). | Its row under the monument card shows the obelisk standing at Luxor (its monument picture), not the museum court. | The museum picture on a secondary's row: `gm_mon_row_site` uses the trophy type. |
| **The Venus de Milo home (2026-10-16).** Return her to Greece (Return Cultural Property, or debug). | Her row and the West Aegean Islands' state card show her armless on a pedestal among the island's ruins, not the bronze rider stand-in. | The stand-in: `gm_state_picture_landmark` for `venus_de_milo` (code 1,000,035). |

## Carrying off

| Check | Expect | If it fails |
|---|---|---|
| **Occupation at all** (log triage, 2026-10-16). Until then no occupier was ever found (`gm_occupation_read` above), so the occupation rows below could not pass. Occupy half the provinces of an enemy's state that holds a monument. | Within a month a player gets the offer (`monument_trophy_events.1`) and Carry It Off shows on the state's card; an AI occupier carries one off now and then. Under half the provinces: neither. | The offer comes but no button: the buttons read `gm_state_tr_occupied_by` from a scripted GUI, where the script value's province read may come back empty (as `state_unemployment_rate` does, `scripting_best_practices.md`). Give the button a variable the monthly pass sets instead. |
| **One of two.** Occupy a state with a primary and a secondary monument. Use Carry It Off on the secondary's row. | Only that one goes: the building loses its levels (or a quarter or a tenth, by form), the primary and the others stay, the taker's capital shows the trophy. The state is spared for ten years after a piece. | The whole building gone: the click named the primary. |
| **The primary whole.** Carry off a primary whose form goes whole (a column) in a state with a secondary. | The largest secondary becomes the state's monument, with its name, picture and dedication, and the building is at the levels of all that remain. | An empty state: `gm_state_promote_secondary` did not run (it needs `gm_state_has_secondary`). |
| **Tear Down.** Pull down the primary of a state with a secondary. | The same as above. | |
| **Rededicate.** Rededicate the primary of a state with a secondary. | Dedicated again, the primary keeps half its levels and grandeur; the secondaries keep theirs; the cost is 500 a level of the primary's own. | Half of everything: `gm_state_apply_rededicate` read the whole state. |
| **The AI.** Let an AI occupy such a state for a few years. | It carries off a monument now and then, any one of them. | |
| **The AI beside a shrine** (review 2026-10-16). Let an AI occupy a state whose primary is a Grand Shrine or undedicated, with a secondary beside it. | It carries off the secondary now and then (`gm_state_tr_any_takeable`); the shrine stays. A player occupier gets no offer event there (it names the primary), but the secondary's row has Carry It Off. | Never looted: the roll still gates on the primary. |

## Panels

| Check | Expect | If it fails |
|---|---|---|
| **State card.** Open the state view of Upper Egypt with the Obelisk home. | One monument card: Karnak's picture and details as before, with Grandeur at the whole level (its hover names the first one's part and the others'), then under them, inside the same card and across its width, Also Standing Here with a row for the Obelisk. Below the card, Trophies on Display. A state with one monument looks as it did. | A raw key: the loc did not load. A row narrower than the card, or the section's text running over the picture: the vertical wrapper's width (530) or the row widths (480) are wrong. |
| **Our Monuments.** Open the journal entry's Our Monuments, and the Timeline Extended window's Grand Monuments tab. | A row per state's primary as before, then a row per secondary with where it stands. A change in one shows in the other. | |
| **A civil war.** Have a civil war's winner take such a state. | The rows are back within a month (the pass rebuilds the lists). | Rows missing for good: check `gm_mon_lists_written`. |
| **Pictures.** A returned landmark whose picture was drawn later. | It shows the right picture within a month. | |

## Civil wars (2026-10-25, #1136)

A civil war's winner takes over the monuments the loser raised at the win, wherever they stand
(`gm_repair_after_civil_war`), because the loser is deleted within about two weeks and nothing can name it after that.

| Check | Expect | If it fails |
|---|---|---|
| **A late arrival.** Let a revolution win in a country whose regime or Grand Shrine monument stands in a state a third country holds (conquered before the war). Wait until the loser is gone (about two weeks; `scripts/analysis/save_country_probe.py` shows when), then take that state back by treaty or peace deal. | The monument is the winner's own: a shrine is not heritage, and a regime monument is contested only if its message doesn't fit the winner's laws. The state's `gm_raised_by` names the winner. | A shrine turned heritage or a fitting monument contested: the raiser was not rewritten at the win. Check that `TE_CIVIL_WAR: the loser resolves at on_civil_war_won and is dead` was logged. |
| **Beside another.** The same with a monument beside another in that state, or one carried off as a trophy before the war. | The same for its row, and for the trophy once it is returned. | The same; its record is `gm_tr_raised_by`. |
