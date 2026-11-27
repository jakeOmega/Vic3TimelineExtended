# War Wounded play-test checklist

What the next play-test should look at in vanilla's War Wounded journal entry (`je_war_nursing`) as the mod restates it
(`common/journal_entries/te_vanilla_war_nursing.txt`, 2026-11-14): Medevac Helicopters counts as medics when the entry
starts and completes it as Field Hospitals does. In-game checks do not gate a merge (CLAUDE.md, "In-game checks:
self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each PR
adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **A quick case.** Any country with 30 or more battalions. In the console, research `triage`, `modern_nursing` and
  `advanced_military_aircraft` (Medevac Helicopters), and make sure the market sells fabric, liquor, tools and
  aeroplanes (Medevac's `possible`) and opium (Field Hospitals'). Go to war and put a general at a front.
- **Where to look.** The journal's War Wounded entry: its completion conditions while active, the outcome's effects,
  and the Modern Nursing event (`nursing_events.4`) it fires.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `nursing_events`, `complete_nursing_war`,
  `ongoing_war_state` and `je_war_nursing`.

## First release (2026-11-14)

| Check | Expect | If it fails |
|---|---|---|
| **No start on Medevac.** Every formation at a front on Medevac Helicopters, at war. | The entry doesn't start. With one formation on no medic option, it does, and Disease Among the Wounded (`nursing_events.1`) fires. | It starts with every formation on Medevac: `te_formation_has_medic_support = no` isn't read in `possible`; check `debug.log` for a scripted-trigger error. |
| **Conditions.** Hover the active entry's completion. | Three lines under "one of": Field Hospitals used by at least 20% of battalions (currently N%), the same for Medevac Helicopters, and "Together, Field Hospitals and Medevac Helicopters are used by at least 20% of battalions". Then the general check, naming both options. | The custom line shows the 19 rungs or a raw key: the `custom_tooltip` didn't take; read `je_war_nursing_combined_medic_share_tt` in the loc. |
| **Medevac completes.** 20% or more of battalions on Medevac, a Medevac general at a front, no Field Hospitals anywhere. | The entry completes, and Modern Nursing names the war and is placed at a state of its front. | The war's name blank or the event unplaced: the scopes the outcome saves didn't reach the event. Save them as the event does instead, in a copy of `nursing_events.4` the entry fires. |
| **A mixed army.** About 10% on Field Hospitals and 10% on Medevac (12% and 9% is a case off the even split). | The entry completes once the two shares add to 21%; at exactly 20% it may or may not, as the ladder steps in 1%. | It never completes on a mix: the rungs don't add; fall back to each option alone reaching 20% (the first two lines) and say so in `war.md`. |
| **Field Hospitals as before.** 20% on Field Hospitals, a Field Hospitals general. | Completes as in vanilla. | — |

## The Tsar's Rail Transport button counts Air and Space Transport (#1796, 2026-11-27)

Not War Wounded, but the same kind of fix: vanilla's Heir of Alexander agenda (`je_tp_tsar_heir_of_alexander`, Russia
with the Tsar-points content) asks for 75% of battalions on Rail Transport in its third button, which the mod restates
(`common/scripted_buttons/te_vanilla_tsarpoints_buttons.txt`) to count Rail, Air and Space Transport together
(`te_army_rail_or_better_share`). A quick case: Russia with the agenda, `wargaming` and `commercial_aviation`
researched, aeroplanes for sale in its market.

| Check | Expect | If it fails |
|---|---|---|
| **Rail as before.** 75% or more of battalions on Rail Transport. | The button's conditions pass that line, as in vanilla. | — |
| **Air alone.** Every formation moved to Air Transport. | Under "one of": Air Transport used by at least 75% of battalions (currently N%) passes, and the button is possible if its other lines hold. | It fails: the trigger didn't load (look for `te_army_rail_or_better_share` in `error.log`). |
| **A mix.** About 40% on Rail and 40% on Air. | The custom line, "Together, two of Rail Transport, Air Transport and Space Transport are used by at least 75% of battalions", passes; at 75% exactly it may not, as the ladder steps in 1%. | It never passes on a mix of 76% or more: the shares don't add, so a formation holds more than one option; count by formation instead. |
