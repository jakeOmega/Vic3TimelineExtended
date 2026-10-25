# Colonial wars play-test checklist

What the next play-test should look at for the colony test and the wars of independence (2026-10-24,
`docs/superpowers/specs/2026-10-24-colonial-criteria-and-independence-wars-design.md`; `mod_systems.md` § What a Colony
Is and § Wars of Independence). In-game checks do not gate a merge (CLAUDE.md, "In-game checks: self-checks and the
play-test list"): both landed on the offline gate, and this list holds what only the game can show. Add new sections
newest last, and strike through a fixed item with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **The census.** `event te_debug_colonial_empire.4` re-runs the separation pass and writes `TE_CE_CENSUS` lines to
  `debug.log`: one per country holding a non-homeland state of 100,000 people or more, one per such state with each
  part of the colony test as 1 or 0 (`separated`, `distinct`, `settled`, `unincorporated`, `indigenous`, `disparity`,
  `eligible`, `colony`). Option b runs it for us only.
- **A war.** A 1950s save of an empire with a colony below bar 40 whose people are severely unaccepted: France with
  Algeria, Portugal with Angola. `event te_debug_colonial_empire.1` (option d, Crumbling 30) puts the bar below 40;
  `event decolonization_events.70` fires a declaration for the territory most likely to rise.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `TE_SELF_CHECK`, `TE_CE_CENSUS`, `TE_DECOL_IW`,
  `dp_te_colonial_war`, `te_colonial_reconquest`, `decol_iw_`, `Failed to fetch` and `decolonization_events.7`.

## Self-checks

Each is a once-a-game `debug_log` line, `TE_SELF_CHECK OK|BROKEN <name>` with the numbers, logged only once the case
has happened (a declaration fought, talks concluded), so OK cannot be a false pass.

| Self-check | When it logs | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `decol_iw_war_started` | the first war of a territory's rebels to begin (OK), or 30 days after Fight with no war (BROKEN) | a play created from our scope the day after the rebels form becomes a war (`.71`, `decol_iw_open_war`) | the play did not start a war: the rebels are free with no war, and leave as a release would (`decol_iw_end_unstarted`) | create the war from the rebels' scope (vanilla's Sepoy shape) with a play of their own whose goal is independence, not annexation |
| `decol_iw_rebels_armed` | two months into a territory's rebels' first war | the rebels have an army (`any_military_formation = { is_army = yes }`) | a new dynamic country does not build one in time | seed one with `create_military_formation` in `decol_iw_rebels_formed` |
| `decol_iw_talks_peace` | when a war ends after the accords (OK), or six months after the accords with the war still on (BROKEN) | a dropped goal (`decol_iw_conceded` makes `te_colonial_reconquest` invalid) lets the war end in a white peace | the engine kept the war going with no goal against the rebels | talks end the war only by the player's peace offer; an AI's talks just lower the drain (the conceded war already drains at `decol_iw_bar_drain_per_war_in_talks`) |

## The colony test (2026-10-24)

| Check | Expect | If it fails |
|---|---|---|
| **The census at 1836.** Run `.4` on day one. | France's Algerian states, Japan's or Britain's island holdings where history gives them, and Portugal's African and Asian territories read `separated=1 distinct=1`; British Ireland reads `separated=1 distinct=0`; Russia's Central Asia and China's Tibet read `separated=0`. | Every state `separated=0`: the game-start pass did not run (`colonial_geography_game_start_on_action`), or `var:ce_separated ?= scope:ce_sep_owner` does not compare a stored country (save it as a variable flag on the state instead and clear it on a change of owner). |
| **Straits.** Japan, Denmark, the Ottomans, Italy, Spain with the Rif. | Kyushu, Shikoku and Hokkaido, Jutland and Scania, Anatolia across the Bosporus, and Sicily read `separated=0` for their own country; the Rif, Ryukyu and Sakhalin `separated=1`. | A homeland island `separated=1`: the fill's own crossing (`ce_fill_homeland_strait`) did not fire, or the endpoint tag (`ce_strait_end`) is missing; a non-homeland crossing `separated=0`: `ce_fill_land_link` let it through. |
| **Protectorates.** France with Tunisia or Morocco, Britain with Egypt, as protectorates. | Each is a colonial subject (the Colonial Holdings subject list; `colonial_subjects=` in the census). | Missing: `ce_subject_separated` was not written (the overlord's pass, step 4), or a land border to a linked state of the overlord's counts. |
| **An old save.** Load a save from before this change with the entry running. | The entry keeps running; the first monthly pass fills the cache (`cached=1`). | The entry ended with Voluntary Decolonization (`.206`) on load: the fail's guard (`has_variable = ce_separation_cached`) did not hold. |
| **The panel.** Colonial Holdings' rows. | A colony that is only unincorporated shows its icon lit; its hover counts the unincorporated states. | The icon dimmed on such a row: `colonial_bloc_disp_colony` / `colonial_bloc_unincorporated`. |
| **Cost.** A large empire's monthly tick, before and after. | No visible slowdown on the monthly pulse. | A slow tick: profile `ce_refresh_separation` (the `while` ring fill) and drop its prefilter to countries with the decolonization technology, accepting that the naval laws' AI weights read stale colonies before it. |

## Wars of independence (2026-10-24)

| Check | Expect | If it fails |
|---|---|---|
| **A declaration.** `.70` for a colony. | A popup at the territory naming its people and the states it would take; Concede, Negotiate and Fight, Fight's hover saying what a war means; with settlers, the settlers' text. | A blank people name: the preview (`_decolonization_preview_region`, region 1) did not run in `immediate`. |
| **Fight.** Choose it. | The next day: a war, "War of Independence", against the new country, with our goal Reconquer; the rebels hold Fighting for Independence; a notice to every great power; the panel's Wars of Independence block shows the row. | No war: the `decol_iw_war_started` self-check's BROKEN line. A war with extra goals: `initiator_can_add_war_goals` / `target_can_add_war_goals` were ignored. |
| **Our formations.** Ours in the colony at the declaration. | They stay on the new front, or are pulled to another headquarters. | Either is acceptable; if pulled, the war opens with a landing: say so in the player guide's chapter 12. |
| **The AI lands.** A fast AI run with an AI France facing an Algerian declaration it fights. | The AI sends an army across the sea. | It never lands: give the AI's Fight a lean to concede when its navy cannot reach (a script value of the colony's sea access). |
| **Occupation.** Occupy the whole territory. | The war goes on: the goal does not self-enforce. | It ended on occupation: the goal carries a mirror after all; remove the contestion as well. |
| **Winning.** Force the rebels to capitulate (or annex them in the peace). | Order Restored (`.72`): the territory is ours, radicalized, and no declaration from it for ten years. | No `.72` within a month: `on_enforced` or the monthly check (`decol_iw_state_N` owned by us) failed; read `TE_DECOL_IW: reconquest enforced`. |
| **Losing.** Capitulate, or sign a white peace. | The Flag Comes Down (`.73`): the lost-war modifier, the Armed Forces' anger; the new country with Bloody Decolonization's legacy and junta laws; the Nationalization Question a week later. | A record that never settles: the war's end was not seen (`decol_iw_slot_at_war`). |
| **War support.** Hover our and the rebels' war support. | Ours: "A war to keep a colony", "The world condemns it" with condemners, "Settlers to defend" with settlers. Theirs: "Fighting for independence", "Foreign arms" with a backer. | A missing line: `zz_te_war_support_injections.txt`'s `scope:war` participant test. |
| **The bar.** Hover the stability bar during a war. | "Wars of independence" at −0.5 a war, beside the at-war term. | Missing: `decol_iw_running` was not counted. |
| **Open Talks.** Press it on a war row. | `.80`; after six months the accords notice, the goal gone from the war, and a white peace accepted by the rebels; then `.76`. | See `decol_iw_talks_peace`. |
| **A great power arms the rebels.** With an anti-colonial great power. | `.74` for it; Arm moves a monthly sum from its treasury to the rebels' and gives them Foreign Arms; the row's Backers counts it. | No payment: `decol_iw_backer_monthly` (the backer's `decol_iw_arming`). |
| **Intervene's guard.** With an anti-colonial great power that is our ally, then one that is our rival with a larger army. | The ally sees Intervene greyed with its reason; the rival can intervene and joins the war on the rebels' side. | Joins as an ally of ours: `decol_iw_can_intervene`; does not join: `join_war`'s `side`. |
| **The regime crisis.** Four years at red war support. | The Captains' Revolt (no voting law) or the Republic in Danger (a voting law), with its law change. | The law did not change: `activate_law` refused it (a law the country cannot hold); fall back to the modifiers alone. |
| **The wave.** Drop the bar to 0 with three or more territories. | The empire collapses, then up to three declarations two months apart, worst first; conceding all three is the old collapse. | All three at once, or none: `.77` and `decol_wave_left`. |
| **A colonial subject's war.** A Colony subject at high liberty desire starts its independence play and we fight. | The war appears in the Wars of Independence block (no Open Talks); the subject fights with the fighters' package; its ending fires `.72` or `.73`. | No row: `decol_iw_track_subject_wars`. |
| **A colonial secession.** A secession in a separated, distinct colony. | A row for the secessionists; their defeat gives `.72`, their win `.73`. | No row: at `on_secession_start` the capital's `ce_separated` no longer named us. |
| **A revolution mid-war.** A revolution wins while a war runs. | The winner keeps the war's row and the home front's modifier at once. | The modifier gone for a month: `decol_iw_repair_after_civil_war`. A record that settles as a loss: the winner is not at war with the rebels (expected, per the design). |
