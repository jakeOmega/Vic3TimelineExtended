# Tourism play-test checklist

What the next play-test should look at in the tourism card. In-game checks do not gate a merge (CLAUDE.md, "In-game
checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here.
Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** Open a state's panel; the tourism card sits above the status grid. Its Throughput column lists the
  sources, and the footer's "All modifiers" line shows what the engine applied (up to a month behind the sources).
- **Logs.** Read `debug.log`, not `error.log`.

## Excess infrastructure replaces Ports and Transit

The Ports row (per Port level) and the Transit row (per Railway and Highway level) became one Excess Infrastructure
row: `E / (E + 30000)`, where E is the state's infrastructure less its usage, floored at 0
(`tourism_throughput_from_infrastructure` in `common/script_values/tourism.txt`). The 30000 is the owner's figure. Nothing
in the offline gate can tell whether it suits real states, because the repo holds no late-game save. For scale, a state
with about a hundred levels each of Port, Railway and Highway used to read +40%; it now needs about 20,000 spare
infrastructure to read the same.

| Check | Expect | If it fails |
|---|---|---|
| **Scale.** In a developed late-game state, read the row's value beside the state's infrastructure and usage (the vanilla state panel shows both). | The row equals `spare / (spare + 30000)`: about +9% at 3,000 spare, +25% at 10,000, +50% at 30,000, +75% at 90,000. The bar is half full at 30,000. | A wrong figure means the script value is not reading the state's balance: check the scope the monthly pulse evaluates it in. |
| **Calibration.** Compare developed states across a game: a core industrial state, a rail-heavy agricultural one, a tourist coast. | Note the spread. A state that overbuilt rail reads high; a crowded industrial one reads near 0. With the half-point at 30,000, a state with only a few thousand spare reads under +10%, so tourism throughput may fall in most states against the old Port and Transit rows. | Most developed states under about 5% or over about 60%: move the half-point. It is in `tourism_throughput_from_infrastructure` and `tourism_fill_infrastructure_pct`; the same figures are in `te_state_tourism_infrastructure_tt`, `docs/player_guide/08-states.md` and `docs/systems/mod_systems/dynamic_modifier_pattern.md`. |
| **Negative balance.** Find a state whose usage exceeds its infrastructure (market access under 100%). | The row reads +0%, not a negative figure. | A negative figure means the floor is missing from `tourism_excess_infrastructure`. |
| **Coastal states.** A coastal state with a large Port and little rail. | It no longer gets a bonus for the Port as such; a Port adds only the few points of infrastructure it supplies. This is intended. | Tourist coasts that read badly low are a calibration question for the owner, not a bug. |
| **Refresh.** Build or demolish a Railway, then wait for the next month. | The row and the "All modifiers" throughput line move together after the monthly pulse. | A row that moves while "All modifiers" does not means `tourism_on_action` did not re-apply the modifier. |
| **Display.** Hover the row's label and its bar. | The label reads "Excess Infrastructure"; the hover text gives the three sample points and "Maximum: +100% (approached, never reached)". The concept's link opens its description. | A raw key (`concept_tourism_infrastructure`, `te_state_tourism_infrastructure_tt`) means the loc did not load. |

## Highway methods add to tourism output

The five Highway production methods carry `goods_output_tourism_mult` in their `state_modifiers`, the same slot the
Airport and Spaceport use: +5% on Civil, Electric Civil and Autonomous, +2.5% on Industrial and Electric Industrial
(`common/production_methods/extra_pms.txt`).

| Check | Expect | If it fails |
|---|---|---|
| **Value.** Build a Highway on the Civil Highway method in a state, staff it, then read the tourism card's "All modifiers" output line (hover for the breakdown). | The Highway appears as a source of about +5% per level, scaled by staffing. Switching to Industrial Highway halves it to +2.5%. | A missing source means the method's `state_modifiers` block did not load: check `debug.log` for the PM. |

## Monuments move to output, heritage leaves base appeal

Tourism heritage phase 1 (`docs/superpowers/archive/specs/2026-10-23-tourism-heritage-design.md`): a monument's tourism is an
output bonus, and the heritage the existing landmarks, sites and 1836 wonders stand for comes off Base Appeal through
`tourism_heritage_moved` (`common/script_values/tourism_heritage_generated.txt`). Figures are at the Standard policy;
Open to the Public multiplies a Grand Monument's steps by 1.5, and an AI that has a monument beside a Tourism Industry
plays Open.

| Check | Expect | If it fails |
|---|---|---|
| **Attica, day one.** Open Attica's state panel. | Base Appeal reads +60%, and its tooltip says 40% of it is counted in its monuments. The output "All modifiers" line shows the Grand Monument at +40% (four steps of the Parthenon's 50 grandeur), plus Ancestral Antiquity's +5% a step. | Base Appeal at +100% means `tourism_heritage_moved` reads 0: check `gm_landmarks_seeded` is set and the rule is on. A Grand Monument line in throughput means `gm_local_tourism` did not change. |
| **A state with nothing moved.** Hover Base Appeal in Nebraska. | The tooltip has no "counted in its monuments" line. | A "0%" line means the `SelectLocalization` in `te_state_tourism_appeal_tt` didn't pick the empty key. |
| **Agra.** Open Agra's panel. | The output column's Monuments row reads +40% (the Taj Mahal); Base Appeal reads +45%. | Monuments at +10% means `is_building_type` did not match inside `every_scope_building` in `tourism_bonus_from_monuments`; the eight wonders all fall to the default. |
| **Another monument.** A state with a later wonder (the Eiffel Tower, a mod wonder). | Monuments reads +10%. | — |
| **Rule off.** Start a game with the Grand Monuments rule disabled; open Attica and Agra. | Attica's Base Appeal reads +100%; Agra's still +45% (the Taj Mahal is vanilla's). | Attica below +100% means the landmark gate isn't reading the rule. |
| **Eastern Mali.** Before and after the Great Mosque of Djenné is built. | Base Appeal +45% until it stands, then Monuments +20%. Western Mali's Base Appeal reads +45% throughout (rescored: Djenné was never there). | — |
| ~~**Moscow.** Open Moscow's panel.~~ | ~~Base Appeal +65%; Monuments +20% (Saint Basil's). The Kremlin's 20 stay in Base Appeal until phase 2 adds it.~~ Superseded by phase 2 (below): +45%, with the Kremlin's two steps. | — |
| **Skyscraper.** A state with a Skyscraper. | The throughput column's Skyscraper row reads +10%, with its tooltip. | A raw key means `te_state_tourism_skyscraper_lbl` or `_tt` did not load. |

## To History: the heritage landmarks and sites

Tourism heritage phases 2 and 3 (`docs/superpowers/archive/specs/2026-10-23-tourism-heritage-design.md` §§ 7, 9): 51
landmarks stand To History on 1 January 1836 and 14 buried sites come up To History when dug, each taking the Base
Appeal of the heritage it stands for (`tourism_heritage_moved`, gated on `gm_landmarks_seeded_2` for the landmarks and
on the rule for the sites). Every monument policy counts To History at half. Figures are at Cultural Promotion, the
default; the AI plays Open beside a Tourism Industry.

| Check | Expect | If it fails |
|---|---|---|
| **Lower Egypt, day one.** Open its panel and its Grand Monument card. | The Pyramids of Giza stand for Egypt, named, dedicated To History, with its own picture (the three pyramids and the Sphinx). Base Appeal reads +50%; the Grand Monument line +50% (five steps of 75 grandeur). | No monument: `debug.log` has `TE_MONUMENTS: landmark pyramids_of_giza not placed`. Base Appeal at +100%: `gm_landmarks_seeded_2` isn't set (`gm_landmarks_on_game_started_after_lobby`). |
| **Placed everywhere.** Search `debug.log` after the first day for `TE_MONUMENTS: landmark` and `not placed`. | 51 new `placed` lines and no `not placed` for a To History key. Split states: Sana'a under the Zaydi imam and Shibam under Kathiri (Yemen), Fasil Ghebbi under Begemder (Gonder), the Mausoleum of Sultan Sanjar under Bukhara (Merz), the Walls of Tallinn under the United Baltic Provinces. | A `not placed` line means that owner proved wrong in this vanilla version: fix its `TAG` in `gm_seed_landmarks` and the `LANDMARKS` row. |
| **Petra beside the Mesha Stele.** Transjordan's card and Also Standing Here. | The Mesha Stele first (War Memorial), Petra beside it, To History. Base Appeal +60%; the Grand Monument line +30% (three steps of 40 grandeur). | Petra missing: the beside seeding failed (`gm_seed_landmark_beside`). |
| **Kyoto and Kansai.** Both panels. | Kyoto: Kinkaku-ji, Base Appeal +60%, Grand Monument +40%. Kansai: Tōdai-ji at Nara, Base Appeal +90% unchanged, Grand Monument +20%. | — |
| **Never contested.** Conquer a state with a To History landmark (Egypt's Aleppo, or a peace deal), and change a government that holds one. | It stays Upheld: no contest, no Pull Down, Rededicate or Keep as Heritage buttons on its row. | A contest means `gm_state_is_bound` counts `pm_monument_historic`. |
| **Not in the ceremony.** Dedicate one of your own construction sites. | The ceremony lists the twelve dedications; To History isn't among them. | — |
| **Policy at half.** Switch Egypt to Open to the Public and hover Lower Egypt's monument tourism next month. | The factor reads ×1.25, with the line about To History at half; Transjordan's ×1.41 (Petra's 15 of 40 grandeur). Under State Ceremonial the legitimacy hover's ceremonies line says To History counts at half. | ×1.5 means `gm_policy_factor_tourism_here` isn't read by `gm_state_monthly`. |
| **A dug site's tourism.** Dig Ephesus (Empiricism) or any To History site. | Its state's Base Appeal is lower from the start (Aydin +70%) and stays so; once dug the site stands To History at 3 levels and the state's Grand Monument line rises. | A site dug To the Nation means `gm_arch_seed_site`'s `DEDICATION` didn't reach `gm_tr_dedication`. |
| **Hampi.** Kurnool and Mysore. | Hampi's site lists under Kurnool (Bellary); Kurnool's Base Appeal reads +50% until it is dug, Mysore's +75%. | — |
| **An older save.** Load a save from before this change. | No new landmarks, and their states keep their Base Appeal (Lower Egypt +100%). The To History sites appear from the first monthly pass (seed round 4), and their states' Base Appeal drops by their points at once. `event te_debug_monuments.5`, option a, places the landmarks and sets the flag. | Lower Egypt below +100% without Giza: the landmark gate isn't reading `gm_landmarks_seeded_2`. |
| **Pictures.** Look at a few rows of new landmarks. | Each shows its own picture with its grandeur frame, none a draped placeholder or a stand-in; a trophy carried off from one shows its own trophy picture. | The draped picture means its code in `gm_state_picture_landmarks` has no icon in the `gm_picture` widget. |
