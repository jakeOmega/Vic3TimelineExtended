# Nuclear Weapons GUI: Icons

The overview at the top of the Nuclear Weapons journal entry (`je_nuclear_program`) draws 24 icons: one per state of the programme and of the posture, plus the warheads and crisis cells. All of them are placeholders: textures the mod or vanilla already uses elsewhere, chosen so the layout can be judged in game before the art exists (style guide rule 10). This page lists every one, what the final art should show and a proposed path, as `un_gui_icons.md` did for the UN before PR #572 replaced its placeholders.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/nuclear_overview_widget.gui`, one icon widget per state, picked by a display value's code (`EqualTo_CFixedPoint( …ScriptValue('<code value>'), '(CFixedPoint)N' )`). No script reads the paths, so swapping one in is one path change. `OverviewTest` in `test_nuclear_layout.py` checks that each code draws exactly one icon and that every texture in the overview is listed on this page.

**The rule for the set** (from the UN's): simple and easy to recognize at 36 px. The states of one thing share an emblem and differ by a mark. Proposed home: `gfx/interface/icons/nuclear_icons/`.

## Row 1: the programme

Code: `nuclear_program_display_state` (`common/script_values/extra_script_values.txt`), in the order of the status line's programme sentence (`nuclear_program_status_line`). The cell's hover is that sentence.

| Code | State | Placeholder now | Final art should show | Proposed file |
|---|---|---|---|---|
| 0 | Unfunded | `gfx/interface/icons/generic_icons/paused.dds` | a steel warhead casing on a cradle, grey, under a drawn pause mark | `programme_unfunded.dds` |
| 1 | Developing (first device) | `gfx/interface/icons/invention_icons/nuclear_weapons.dds` | the warhead casing with an open inspection panel and a brass wrench beside it | `programme_developing.dds` |
| 2 | Producing (series production) | `gfx/interface/icons/event_icons/mushroom_cloud.dds` | three identical steel warheads standing in a row | `programme_producing.dds` |
| 3 | Frozen (pause treaty) | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_program_pause.dds` | the warhead casing behind a blue ribbon with a wax treaty seal | `programme_frozen.dds` |
| 4 | At ceiling | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_arms_limitation.dds` | a row of warheads under a flat gold bar at their tips | `programme_at_ceiling.dds` |
| 5 | Dismantling | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_disarmament.dds` | the warhead casing split in two halves, a wrench between them | `programme_dismantling.dds` |
| 6 | No programme | `gfx/interface/icons/invention_icons/nuclear_weapons.dds` (30% opacity) | the warhead casing, faint grey, no mark | `programme_none.dds` |
| 7 | Renounced | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_disarmament.dds` | a white dove over a broken warhead casing | `programme_renounced.dds` |
| 8 | Disarmed (settlement or NPT) | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_disarmament.dds` (30% opacity) | the warhead casing, grey, under vanilla's red cross | `programme_disarmed.dds` |

## Row 1: warheads and the crisis

| Cell | Shown | Placeholder now | Final art should show | Proposed file |
|---|---|---|---|---|
| Warheads | always | `gfx/interface/icons/invention_icons/guided_missiles.dds` | a single steel warhead, nose up, with a small radiation trefoil | `warheads.dds` |
| Crisis | while in one | `gfx/interface/icons/diplomatic_action_icons/nd_nuclear_ultimatum_action.dds` | the warhead under vanilla's warning mark, on a red disc | `crisis.dds` |

The credibility cell is a meter, not an icon.

## Row 2: the posture (while armed)

Codes: `nd_display_doctrine_code`, `nd_display_readiness_code`, `nd_display_authority_code` (`common/script_values/nuclear_deterrence_values.txt`), falling back as the name blocks in `nuclear_deterrence_custom_loc.txt` do. Each cell's hover is the posture row's own tooltip.

| Axis | Code | State | Placeholder now | Final art should show | Proposed file |
|---|---|---|---|---|---|
| Doctrine | 1 | No First Use | `gfx/interface/icons/diplomatic_treaties_articles_icons/crisis_resolution.dds` | a warhead inside a closed gold shield | `doctrine_nfu.dds` |
| Doctrine | 2 | Existential Deterrence | `gfx/interface/icons/diplomatic_treaties_articles_icons/nuclear_guarantee.dds` | a warhead behind a stone wall, nose up | `doctrine_existential.dds` |
| Doctrine | 3 | Flexible First Use | `gfx/interface/icons/diplomatic_action_icons/nd_nuclear_warning_action.dds` | a warhead tilted forward on a half-drawn shield | `doctrine_flexible.dds` |
| Doctrine | 4 | Nuclear Compellence | `gfx/interface/icons/diplomatic_action_icons/nd_nuclear_ultimatum_action.dds` | a warhead pointing right past a raised gauntlet | `doctrine_compellence.dds` |
| Doctrine | 5 | Nuclear Warfighting | `gfx/interface/icons/invention_icons/tactical_nuclear_weapons.dds` | a warhead crossed with a sword | `doctrine_warfighting.dds` |
| Readiness | 0 | Recessed | `gfx/interface/buttons/button_icons/lock.dds` | a warhead in a locked steel crate | `readiness_recessed.dds` |
| Readiness | 1 | Routine | `gfx/interface/icons/commander_order_icons/standby.dds` | a missile lying flat on its launcher, green lamp | `readiness_routine.dds` |
| Readiness | 2 | Heightened | `gfx/interface/icons/generic_icons/warning.dds` | the missile raised halfway, amber lamp | `readiness_heightened.dds` |
| Readiness | 3 | High Alert | `gfx/interface/icons/generic_icons/mobilize_icon_single.dds` | the missile upright on its launcher, red lamp | `readiness_high_alert.dds` |
| Launch authority | 1 | Central Authorization | `gfx/interface/icons/generic_icons/government_building_icon.dds` | a single brass key in a government seal | `authority_central.dds` |
| Launch authority | 2 | Conditional Delegation | `gfx/interface/icons/generic_icons/most_senior_front_commander.dds` | the brass key handed from a gloved hand to an officer's | `authority_delegation.dds` |
| Launch authority | 3 | Launch on Warning | `gfx/interface/icons/lens_toolbar_icons/nd_nuclear_warning_action.dds` | a radar dish with the brass key under it | `authority_on_warning.dds` |
| Launch authority | 4 | Automatic Retaliation | `gfx/interface/icons/generic_icons/observer_mode_icon.dds` | a grey machine cabinet with the brass key turned in it, red lamp | `authority_automatic.dds` |

## Row 3: the nuclear taboo

No placeholder: the bar and its target marker are vanilla's (`progressbar_marker.dds`, as the UN overview's authority bar uses), and the trend arrow is vanilla's `trend_up` / `trend_down` / `trend_nochange`, picked by `nd_disp_taboo_trend`.
