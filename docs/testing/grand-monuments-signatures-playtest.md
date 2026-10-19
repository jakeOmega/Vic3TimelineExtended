# Grand Monuments: unique dedications, specials and historical opportunities, play-test checklist

What the next play-test should look at for the signatures work (spec
`docs/superpowers/archive/specs/2026-10-16-grand-monument-signatures-design.md` §13). In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): the PR lands on the offline gate and this is what
only the game can show. A fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work".
- **Start a game in 1836** with the Grand Monuments rule on. China (the Temple of Heaven), Britain (four trophies with
  signatures) and Bavaria (Walhalla's offer) cover most of the list; France has the Arc de Triomphe.
- **Logs.** Read `debug.log`; grep `TE_MONUMENTS: signature` and `TE_MONUMENTS: sig`.
- **Console.** `event te_debug_monuments.8`: (a) hold one of every special, (b) run the landmark and trophy backfill
  now, (c) give the tallest monument the next signature in the table, (d) print every signature's total and every
  monument's signature, parent and whether it counts (1 nationally, 2 locally only, 3 dormant).

## Rendering

| Check | Expect | If it fails |
|---|---|---|
| **The name and its hover.** China's Our Monuments row and Beijing's state card. | Both read "The Mandate of Heaven". Hovering the name shows To the Crown, the effect, the monument's grandeur and "It counts". | The name reads "To the Crown": the backfill did not run (`gm_state_sig_backfill` in the refresh loop) or `gm_dedication_name`'s signature branches come after the twelve. No hover: the `#tooltippable;tooltip:[State.GetTooltipTag],gm_sig_parent_tt …#!` span does not take in that widget; switch `gm_dedication_label` to `gm_sig_label_plain` there and rely on the row's existing tooltip. |
| **A container's line.** A trophy row (London's Rosetta Stone) and a monument beside another. | The title shows the signature's name; a line under it reads "A unique dedication of …", with the effect on hover. This line is by design: a script container has no tooltip tag for an inline span. | No line: `gm_tr_row_sig` is hidden by `gm_tr_disp_has_sig` reading 0. |
| **The state card rows.** Upper Egypt (the Obelisks of Karnak, Ancestral Antiquity) and any state with an Epigraphic Archive monument. | A Tourism Industry throughput row and a University throughput row, each with its breakdown on hover. | |

## Event text (2026-10-18)

| Check | Expect | If it fails |
|---|---|---|
| **The name in a description.** A monument's form event (`monument_events.24`, "The Form It Takes"), and the anniversary events `.12`–`.15`, which are country events. | The monument's name reads in full (a city-named one as "the <city> <form>"), never "the HUB_NAME__city", and no double space before "in". The name targets now read `ROOT.GetState`; that `ROOT` is the called-on state for a `state` custom loc rests on vanilla's culture and interest-group targets. | `ROOT` there is the event's root, not the state: a country event's name breaks while `.24` (a state event) reads. Give each event context its own family, as the row has. |
| **Keep the name.** `monument_events.25`'s first option. | "Keep the name: the … …", as before (#819). | The splice reads `ROOT.GetState` from the event's own root, which is the state: compare with `.24`. |
| **Why an option is offered.** In the dedication event, hover a greyed dedication (To the Crown in a republic) and an offered gated one (Give It Over to the Arts). In the style event (`.11`), hover an offered style. | The gated dedications, the opportunity's and the held unique dedications show as highlighted (gold); Let It Stand and the ungated ones stay plain. The greyed one: "This option is unavailable because:" with its reason crossed ("Our government is crowned: Monarchy, Social Monarchy or Chiefdom"); the engine prints a highlighted option's failing conditions (seen 2026-10-18). An offered one: "This option is available because:" with the reason as the first line ("We have researched Romanticism"; a style names its language or religion), then the effects. The reason is not listed under the state's name. | The reason under the state's name ("Tunisia • One of our primary cultures speaks…", as on 2026-10-18 before the reason moved to the owner's scope): the engine groups every non-player scope. Fold the reason into the effect's own sentence instead, so the state has one line and no heading. A greyed option showing a reason it doesn't meet: its `if` guard and its trigger have drifted (`OptionReasonTests`). |
| **No error flood.** Leave the dedication event (`monument_events.2`) open on a new monument for ten seconds. | `error.log` has no `gm_skin` lines (it had about 110 a second). | Another `var:gm_skin` read on the tooltip path: search the effects the options call for an unguarded one. |

## Counting

| Check | Expect | If it fails |
|---|---|---|
| **National Effects at the start.** China; Britain. | China shows Seat of the Throne and The Mandate of Heaven. Britain's trophies show Ancestral Antiquity, The Glory of Athens, the Epigraphic Archive, Martial Glory and Seat of the Throne, each small (a trophy counts at half). | Missing rows: read option (d); a trophy whose `gm_tr_signature` is unset missed `gm_tr_sig_backfill`. |
| **Contested and heritage.** Make a crown landmark contested (change the government), then keep it as heritage. | Its national row drops out; a local signature's state card row stays. The same as heritage. | National stays: `gm_state_sig_counts` does not read `gm_state_status_fits`. |
| **Dormant.** Rededicate the Alexander Column To the Republic. | The row reads To the Republic, Royal Pantheon's national row drops out, and option (d) prints it with status 3. | |
| **A piece carried off.** Carry off a quarter of an arch landmark with a signature. | The taker's National Effects gains the signature at the trophy's grandeur; the monument keeps its own at its smaller size. Bringing it home restores the whole. | |
| **Interest groups.** A country with an upheld Ancestral Antiquity or Epigraphic Archive monument. | Intelligentsia approval rises by about 1 per step of that grandeur, in the Interest Group Approval breakdown. | |

## Specials

| Check | Expect | If it fails |
|---|---|---|
| **Completion gives one.** Complete a Victory opportunity. | `monument_events.28` says the memorial is now dedicated To Victory; its row shows To Victory; the next War Memorial ceremony offers no To Victory option. A second Victory completed gives a second memorial To Victory. | No grant: `gm_sig_grant` was not set in `gm_com_fulfil`, or `monument_events.26` ran before it. |
| **Held.** Complete an opportunity with a landmark (it keeps its own signature), or use option (a). | National Effects shows "Held: To Victory"; the next War Memorial's ceremony offers "Dedicate it To Victory" once, and the AI takes it. | The option is visible without a held one: `gm_state_ceremony_offers_special` is not the option's `trigger`. |
| **A once-a-game offer.** Become a great power for the first time. | The offer's tooltip names To the Concert of Nations and says letting it pass loses it for good. | |
| **Old saves.** Load a save from before this change with a boon running. | Within a month every landmark and trophy shows its signature, and a held special appears for each boon still running. | |

## Historical opportunities

| Check | Expect | If it fails |
|---|---|---|
| **Walhalla.** Play Bavaria from 1836, or watch it in observer. | Bavaria is offered Walhalla (To the Nation, 5 levels, the Petty Bourgeoisie). The AI below major power lets it pass, as for any opportunity. | No offer: `has_state_in_state_region = STATE_BAVARIA` or `language_germanophone` fails; read `gm_hist_offered_walhalla`. |
| **Completing it.** Seize it as Bavaria and build the levels. | `monument_events.28` names Walhalla; the new monument becomes Walhalla, with its stand-in picture, its name locked (Rename and Name It greyed) and Heroes of the Nation. | It keeps its unveiling name: `gm_state_become_landmark` did not set `gm_skin` and the namesake. |
| **Lapsing.** As the United States in 1848, take the Washington Monument's offer, then end the republic. | The opportunity lapses. | |
| **The mosque.** Egypt in 1836. | The Muhammad Ali Mosque is offered (a Grand Shrine of 10 levels, the Devout), with twice the usual months. | |
