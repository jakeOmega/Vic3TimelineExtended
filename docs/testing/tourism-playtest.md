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
| **Calibration.** Compare developed states across a game: a core industrial state, a rail-heavy agricultural one, a tourist coast. | Note the spread. A state that overbuilt rail reads high; a crowded industrial one reads near 0. With the half-point at 30,000, a state with only a few thousand spare reads under +10%, so tourism throughput may fall in most states against the old Port and Transit rows. | Most developed states under about 5% or over about 60%: move the half-point. It is in `tourism_throughput_from_infrastructure` and `tourism_fill_infrastructure_pct`; the same figures are in `te_state_tourism_infrastructure_tt`, `docs/player_guide/08-states.md` and `docs/systems/mod_systems.md`. |
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

Tourism heritage phase 1 (`docs/superpowers/specs/2026-10-23-tourism-heritage-design.md`): a monument's tourism is an
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
| **Moscow.** Open Moscow's panel. | Base Appeal +65%; Monuments +20% (Saint Basil's). The Kremlin's 20 stay in Base Appeal until phase 2 adds it. | — |
| **Skyscraper.** A state with a Skyscraper. | The throughput column's Skyscraper row reads +10%, with its tooltip. | A raw key means `te_state_tourism_skyscraper_lbl` or `_tt` did not load. |
