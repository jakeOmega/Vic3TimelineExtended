# Grand Monuments: archaeology, play-test checklist

What the next play-test should look at for the buried sites and the dig (spec
`docs/superpowers/archive/specs/2026-10-14-grand-monument-archaeology-design.md`, issue #939, and the rework
`docs/superpowers/archive/specs/2026-10-16-grand-monument-archaeology-rework-design.md`: innovation the only cost, sized digs, the sites' events,
foreign digs by treaty). In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): the PR landed on the offline gate and this is what only the
game can show. A fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Start a game in 1836** with the Grand Monuments rule on. The sites are seeded by the first monthly pulse, so wait one month
  (or press option a of `event te_debug_monuments.7`).
- **Logs.** Read `debug.log`, not `error.log`; grep `TE_MONUMENTS` and `TE_SELF_CHECK`.
- **Console.** `event te_debug_monuments.7` is the archaeology harness: a seeds the sites and turns up every incidental one; b
  digs the grandest site we may dig by the best method we have; c takes our digs to 99% and runs the pass (they finish); d runs the
  pass and logs the sites that have moved on. Vic3 has no `effect` command.

## Self-checks

Logged once at the start of a game, after the seeding. Nothing logged means the premise was absent (the system is off, or the
site did not seed).

| Line | Means | If BROKEN, take the fallback |
|---|---|---|
| `TE_SELF_CHECK OK/BROKEN archaeology_site_region` | A site's stored state region (`gm_tr_origin_region`, saved from `s:STATE_X` and stored from the saved scope) still finds its states, so a site can be listed, found and dug. | Store the region from a state in it, as the trophies do: `s:X = { random_scope_state = { save_scope_as = … } }` and `value = scope:….state_region` (`gm_state_tr_make_trophy`). |

## Engine facts nobody has seen hold

| Premise | Where it matters | If it fails, take the fallback |
|---|---|---|
| `create_container` with no `parent`, in whatever scope the seeding runs in (no scope from the monthly pass) | The seeding (`gm_arch_seed_site`). Besides the self-check: the Archaeological Expeditions section of a country that owns Mosul (Romanticism) or the Peloponnese (Empiricism). | Make the container in a state's or country's scope, as `gm_state_tr_make_trophy` and `un_resolution_open` do. |
| A retagged container (`remove_tag gm_site`, `add_tag gm_monument`) joins the secondary monuments | A dig finished beside a standing monument (`gm_arch_stand_beside`). | Make a new `gm_monument` container, as `gm_seed_landmark_beside` does, and destroy the site. |
| `chance = <named script value>` in a container scope | The incidental find, and the Antiquarian's destruction. | Roll `random_list` with a literal percentage. |
| `save_temporary_scope_as = gm_arch_cand` in a `limit`, read at once | Who may dig, and who finds (`gm_arch_try_find`, `gm_arch_list_one`): the country as an argument to `gm_arch_has_gate_for`. `gm_tr_holder_owns_origin` does the same. | A saved scope in the effect before the loop. |
| `any_in_list = { variable = … count >= 2 }` after a `has_variable_list` guard | The AI's two-dig cap. | |
| A saved scope per site (`gm_arch_ev_<key>`), cleared and set before `trigger_event`, rides with each popup, so two popups of one month name their own sites | `arch_events.1` and `.2` (`gm_arch_ev_mark`). Two survey sites open in one month for Greece at Empiricism (Mycenae, Olympia): each popup must name its own. | Copy the site's row number to a saved scope value and pick the description by it. |
| `title`/`desc`/`flavor` `first_valid` read saved scopes set by the caller | Both events: the title of a survey find, a ruined dig, a dig abroad, the host's copy. | A separate event per case. |
| `[SCOPE.sState('gm_arch_ev_<key>').GetName]` inside a key pulled in with `$…$` from the event's description | Every site's text names its state. | Name the state in the event's own key. |
| `any_scope_treaty = { any_scope_article = { has_type … source_country = … input_state = … } }` reads an article in force, from a country, in a trigger | Digging abroad (`gm_arch_state_conceded_to`), the free port's sync uses the same shape. | |
| `country_innovation >= <named script value>` is net of the `country_weekly_innovation_add` modifiers (the digs already running); the owner is all but sure it is | The player's launch gate (`gm_arch_spares_<method>`) and the AI's floors (`gm_arch_ai_affords_<method>`). | Subtract `gm_arch_disp_innovation` before comparing. |

## Seeding and listing

| Check | Expect | If it fails |
|---|---|---|
| **First month.** Play as the Ottomans (Mosul, Aydin, Hüdavendigâr, Baghdad) with Romanticism. | The Grand Monuments entry opens with Archaeological Expeditions: *Library of Ashurbanipal* is listed, with the levels it raises and an Antiquarian button. | An empty or missing section: the seeding, or `gm_arch_pass` did not list the country (`gm_arch_listed`). |
| **Empiricism.** Research it. | Troy and Pergamon join (Mycenae and Olympia, in Greece's Peloponnese, for a Greek player); the Systematic button appears. | A site that stays unlisted: the gate (`gm_arch_has_gate_for`) or the ground. |
| **Not our ground.** Play Britain. | No Nineveh: only a country with a part of the ground is offered a site. Foreign digs are deferred. | |
| **Incidental.** Debug a. | The incidental sites in our states whose technology we have are listed with a Launch button; nothing is lost. | |

## The dig

| Check | Expect | If it fails |
|---|---|---|
| **Launch.** Press Systematic on a survey site. | At once: the row moves to the top as a dig ("a Systematic dig, 0% done, about 40 months to go"), a Suspend Dig button appears, and the weekly innovation falls by the amount on the tooltip, 20 (`gm_arch_diversion` on the entry). The Budget's expenses do not change: digs cost no money. The research bar's *cap* is unchanged. | The row staying under the open sites: the pass did not run (`arch_events.10`). A changed cap: a modifier with `max`. |
| **A month.** Wait one. | Progress 2.5% (4% Antiquarian, 3.5% Forensic). | |
| **Suspend.** Suspend it. | It returns to the open sites with "Work paused at …%"; the drain ends. | |
| **Lose the ground.** Cede or lose the state mid-dig. | The dig suspends; the new owner with the technology sees the site open, with the progress kept. | |
| **Finish.** Debug c. | A monument with the site's own name stands in the state (Library of Ashurbanipal, Troy), civic, at its levels (Forensic +2); *An Excavation Is Finished* fires. Mosul and Hüdavendigâr hold no monument in 1836: the building is new. | No building: `gm_state_tr_receive` did not run. A raw key: the loc did not load. |
| **Beside.** As Greece, dig Mycenae, then Olympia (or Delphi beside the Parthenon in Attica). | The building grows by the levels, the first one's dedication kept, and the second is a row in Also Standing Here and in Our Monuments. | The levels lost: `gm_state_tr_add_levels`. |
| **Stratigraphic Destruction.** Dig a 10-level site Antiquarian several times (debug a, b, c). | About one in three comes out at 5 levels with *Stratigraphic Destruction*. | |
| **A looted find.** Occupy a state with a dug site. | Carry It Off offers its piece by name ("Troy — Priam's Treasure"). | The generic part name: `gm_tr_part_name`. |

## Pompeii

| Check | Expect | If it fails |
|---|---|---|
| **1836.** Play the Two Sicilies; wait a month. | Pompeii is a dig in Archaeological Expeditions: "an Antiquarian dig, 33% done" or so, diverting 5 weekly innovation, Suspend Dig. The Budget shows nothing for it. | Not there: the seeding's `excavating` branch (`gm_arch_seed_dig`). |
| **An old save.** Load a save made before Pompeii was added. | A month later Pompeii is a dig of Campania's owner. | `gm_arch_seed_round`. |
| **Restart.** With Empiricism, suspend and press Systematic. | The dig restarts at its progress, slower, and diverts 20 weekly innovation. | |
| **Its pictures (2026-10-16).** Finish the dig (debug c), then carry off a piece. | The monument's row and the state card show the dug-out forum under Vesuvius, not the Latin forum stand-in; the trophy's row shows the battle mosaic in a museum room. | The stand-in: `gm_state_picture_landmark` for `pompeii` (code 1,000,087). The forum without the mosaic: `gm_tr_picture_trophy` (2,000,087). |

## Costs and time

| Check | Expect | If it fails |
|---|---|---|
| **Cost.** Hover the three buttons of a 10-level site (Nineveh). | 5, 20 and 100 weekly innovation and no money; 25, 40 and 29 months. A 5-level site (the Winged Victory) shows the same innovation and 17, 27 and 20 months. | A money figure: an old tooltip. A blank month count: `gm_arch_site_months_*` on the container. |
| **The row.** Launch a dig. | Its row says "Diverts 20 weekly innovation" for Systematic; the summary line's total is the sum of the rows. | A 0: `gm_arch_site_innovation` reads no method. |
| **The gate.** As a country making about 30 weekly innovation with Empiricism, launch a Systematic dig, then hover Systematic on another site. | The first launches; the second button is greyed with "We make at least 20 weekly innovation…" failing, and Antiquarian (5) is still open. | A second launch passes: `country_innovation` is gross, or not refreshed before the next click. |
| **An old save.** Load a save made with the MVP while a dig ran. | Within a month the Excavation Costs modifier is gone from the entry and the Budget's Archaeological Digs row is empty. | `gm_arch_remove_national` did not run, or the engine dropped the modifier on load (harmless). |
| **The AI.** Observe a small AI making under 20 weekly innovation for ten years. | It opens no dig. One making 80 to 400 digs by Systematic; above 400 with Computer Networks, by Forensic. | |

## The events

| Check | Expect | If it fails |
|---|---|---|
| **Survey.** As the Ottomans, research Romanticism (or start with it). | *The Scholars Know Where to Look* names Nineveh, Mosul, the mounds of Kuyunjik and Nebi Yunus, what the scholars expect, and a historical note on Botta, Layard and Rassam; it offers a dig. Once only. | The fallback text: the saved scope did not ride with the event. Another site's text: a scope not cleared. |
| **Two at once.** As Greece, research Empiricism. | Two popups, Mycenae and Olympia, each with its own text and both naming the Peloponnese. | Both naming one site. |
| **Chance find.** Debug a, then wait for a find (or keep the 1% chance). | *Something Under the Spade* with the site's own chance find. | |
| **Finished.** Debug c. | *An Excavation Is Finished* (or *Stratigraphic Destruction*) with the site's find and history, and the monument standing. | |

## Digging abroad

| Check | Expect | If it fails |
|---|---|---|
| **Concession.** As Britain with Romanticism, draft an Excavation Concession with the Ottomans. | Only Ottoman states with a site open to Britain can be picked (Mosul for Nineveh). Britain pays 75 influence. A day after it is signed, Nineveh is in Britain's Archaeological Expeditions with "Abroad, by an Excavation Concession" and launch buttons, and *The Scholars Know Where to Look* fires for Britain. | No state to pick: `gm_arch_state_offers_site`. Not listed: `gm_arch_state_conceded_to` (the treaty read). |
| **Partage.** Dig it, debug c. | Half the levels (5 of 10) stand in Mosul as the Ottomans' monument; a 5-level piece stands in London as Britain's trophy, counting for 3. Britain gets *Our Expedition Returns*; an Ottoman player *A Foreign Expedition Finishes*. The Ottomans may claim the piece with Return Cultural Property. | No trophy: `gm_arch_partage`. The piece not named for its part: `gm_tr_share`. |
| **Permit.** The same with an Excavation Permit (Britain needs Empiricism). | The whole monument stands in Mosul; Britain has Foreign Scholarship (+10 prestige, +1 cultural pull) for ten years. | |
| **Change of heart.** Withdraw from the treaty mid-dig. | The dig suspends with its progress; the Ottomans can take it up. | |
| **A rock-cut site.** A concession at Deir el-Bahari. | No trophy; the site stands whole; Foreign Scholarship. | |
| **Article icons (2026-10-16).** Open a treaty's article list. | Excavation Concession shows a spade by a broken amphora, Excavation Permit a sealed permit with a trowel, Return Cultural Property a bust in a crate, Surrender a Monument a hand lifting a statue. None shares Cultural Exchange's, Seize Company's or the science aid icons. | A borrowed icon: the article's `icon` line. |

## The AI

| Check | Expect | If it fails |
|---|---|---|
| **An AI that digs.** Observe a great power for twenty years. | It opens a dig now and then (not at war, not in default), never more than two at a time, and a finished one stands as a monument. | An AI with five digs: the cap. An AI that never digs: `gm_arch_ai_may_dig` or the list. |

## Panels

| Check | Expect | If it fails |
|---|---|---|
| **Section.** Open the entry, and the Timeline Extended window's Grand Monuments tab. | The section sits after the Opportunity and before National Effects; its header collapses; the digs list above the open sites; rows are 480 wide; the summary and costs lines have tooltips. | A raw key; a row wider than the panel. |
| **Buttons.** Hover Launch and Suspend. | The tooltip names the method, its months, its weekly innovation, and the failing conditions when it is greyed. | |

## Known limits

- A split state is dug by any of its owners, or anyone holding an article on a part of it; the first to launch holds it. An open site's row does not name its state (several countries may hold parts of it).
- No console harness signs a treaty: test digging abroad through the treaty screen.
