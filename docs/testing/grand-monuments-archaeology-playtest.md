# Grand Monuments: archaeology, play-test checklist

What the next play-test should look at for the buried sites and the dig (spec
`docs/superpowers/specs/2026-10-14-grand-monument-archaeology-design.md`, issue #939). In-game checks do not gate a merge
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

## Engine facts nobody has seen hold

| Premise | Where it matters | If it fails, take the fallback |
|---|---|---|
| `create_container` works from `random_country = { }` in a no-scope effect, with no `parent` | The seeding (`gm_arch_seed_site`). No `TE_MONUMENTS` line says it worked: check the Archaeological Expeditions section of a country that owns Mosul (Romanticism) or the Peloponnese (Empiricism). | Make the container in a state's scope instead, as `gm_state_tr_make_trophy` does: `ordered_state = { create_container … }`. |
| `set_variable = { value = s:STATE_X }` stores a state region | Every site's ground (`gm_tr_origin_region`). A site with no ground lists nowhere. | Store the region from a state in it: `s:X = { random_scope_state = { save_scope_as = … } }` and `scope:….state_region`, as the trophies do. |
| `region.any_scope_state` / `random_scope_state` in a stored region | Who may dig, the dig's month, the finishing. | `ordered_scope_state` (proven by `gm_tr_repair_places`). |
| A retagged container (`remove_tag gm_site`, `add_tag gm_monument`) joins the secondary monuments | A dig finished beside a standing monument (`gm_arch_stand_beside`). | Make a new `gm_monument` container, as `gm_seed_landmark_beside` does, and destroy the site. |
| `chance = <named script value>` in a container scope | The incidental find, and the Antiquarian's destruction. | Roll `random_list` with a literal percentage. |

## Seeding and listing

| Check | Expect | If it fails |
|---|---|---|
| **First month.** Play as the Ottomans (Mosul, Aydin, Hüdavendigâr, Baghdad) with Romanticism. | The Grand Monuments entry opens with Archaeological Expeditions: *Library of Ashurbanipal* is listed, with its state, the levels it raises and an Antiquarian button. | An empty or missing section: the seeding, or `gm_arch_pass` did not list the country (`gm_arch_listed`). |
| **Empiricism.** Research it. | Troy and Pergamon join (Mycenae and Olympia, in Greece's Peloponnese, for a Greek player); the Systematic button appears. | A site that stays unlisted: the gate (`gm_arch_country_has_gate`) or the ground. |
| **Not our ground.** Play Britain. | No Nineveh: only a country with a part of the ground is offered a site. Foreign digs are deferred. | |
| **Incidental.** Debug a. | The incidental sites in our states whose technology we have are listed with a Launch button; nothing is lost. | |

## The dig

| Check | Expect | If it fails |
|---|---|---|
| **Launch.** Press Systematic on a survey site. | At once: the row moves to the top as a dig ("a Systematic dig, 0% done, about 40 months to go"), a Suspend Dig button appears, and the Budget's expenses (Archaeological Digs, under Programme Costs in the Breakdown) and the weekly innovation change by the amounts on the tooltip (`gm_arch_expense`, `gm_arch_diversion` on the entry). The research bar's *cap* is unchanged. | The row staying under the open sites: the pass did not run (`arch_events.10`). A changed cap: a modifier with `max`. |
| **A month.** Wait one. | Progress 2.5% (4% Antiquarian, 3.5% Forensic). | |
| **Suspend.** Suspend it. | It returns to the open sites with "Work paused at …%"; the expense and the drain end. | |
| **Lose the ground.** Cede or lose the state mid-dig. | The dig suspends; the new owner with the technology sees the site open, with the progress kept. | |
| **Finish.** Debug c. | A monument with the site's own name stands in the state (Library of Ashurbanipal, Troy), civic, at its levels (Forensic +2); *An Excavation Is Finished* fires. Mosul and Hüdavendigâr hold no monument in 1836: the building is new. | No building: `gm_state_tr_receive` did not run. A raw key: the loc did not load. |
| **Beside.** As Greece, dig Mycenae, then Olympia (or Delphi beside the Parthenon in Attica). | The building grows by the levels, the first one's dedication kept, and the second is a row in Also Standing Here and in Our Monuments. | The levels lost: `gm_state_tr_add_levels`. |
| **Stratigraphic Destruction.** Dig a 10-level site Antiquarian several times (debug a, b, c). | About one in three comes out at 5 levels with *Stratigraphic Destruction*. | |
| **A looted find.** Occupy a state with a dug site. | Carry It Off offers its piece by name ("Troy — Priam's Treasure"). | The generic part name: `gm_tr_part_name`. |

## The AI

| Check | Expect | If it fails |
|---|---|---|
| **An AI that digs.** Observe a great power for twenty years. | It opens a dig now and then (not at war, not in default), never more than two at a time, and a finished one stands as a monument. | An AI with five digs: the cap. An AI that never digs: `gm_arch_ai_may_dig` or the list. |

## Panels

| Check | Expect | If it fails |
|---|---|---|
| **Section.** Open the entry, and the Timeline Extended window's Grand Monuments tab. | The section sits after the Opportunity and before National Effects; its header collapses; the digs list above the open sites; rows are 480 wide; the summary and costs lines have tooltips. | A raw key; a row wider than the panel. |
| **Buttons.** Hover Launch and Suspend. | The tooltip names the method, its months, its weekly cost and innovation, and the failing conditions when it is greyed. | |

## Known limits

- A site shows its form's stand-in picture; none of the 35 has its own.
- Only the holder of the ground digs. A split state is dug by any of its owners; the first to launch holds it.
