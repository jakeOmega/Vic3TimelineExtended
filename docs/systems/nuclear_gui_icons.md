# Nuclear Weapons GUI: Icons

The overview at the top of the Nuclear Weapons journal entry (`je_nuclear_program`) draws 24 icons of its own: one per state of the programme and of the posture, plus the warheads and crisis cells. They were vanilla placeholders through the Nuclear panels' style pass and its play-tests, and PR #586 replaced them. All of them live in `gfx/interface/icons/nuclear_icons/`.

**Where each is set.** Every icon is a literal `texture = "…"` line in `gui/journal_entry_widgets/nuclear_overview_widget.gui`. There is one icon widget per state, picked by a display value's code (`EqualTo_CFixedPoint( …ScriptValue('<code value>'), '(CFixedPoint)N' )`). No script reads the paths. `NuclearIconsTest` in `test_nuclear_layout.py` holds each code to its file. It fails on any placeholder left in the overview and on any icon faded to tell it from another. Once the folder is in the tree, it also checks that every file is there.

**Remaking one.** The icons come from the icon pipeline (`scripts/image_pipeline/`, spec `docs/superpowers/specs/2026-09-26-icon-pipeline-design.md` § "System panels' GUI icons"). Their registry entries are the `nuclear_part` and `nuclear_state` categories in `icon_prompts.py`. `nuclear_part` holds the rendered objects: the warhead, the missile, the key and the things drawn beside them. `nuclear_state` builds each icon from those objects. Each `nuclear_state` entry's `now` field names the vanilla placeholder it replaced. Change the entry, re-render, review, then `write`. The GUI needs no edit unless a file name changes.

**The rule for the set** (the UN's): simple and easy to recognize at 36 px. The states of one thing share an emblem and differ by a mark:
- The programme, the warheads cell, the crisis and the doctrines share one steel warhead. It lies on its side with a small radiation trefoil on its tail.
- Readiness shares the olive-green missile on a drawn steel pad.
- Launch authority shares the brass key.

## Row 1: the programme

Code: `nuclear_program_display_state` (`common/script_values/extra_script_values.txt`), in the order of the status line's programme sentence (`nuclear_program_status_line`). The cell's hover is that sentence. Every state is drawn at full opacity: the art tells No Programme and Disarmed from their neighbours itself, so the 30% fade the placeholders needed is gone.

| Code | State | Shows | File |
|---|---|---|---|
| 0 | Unfunded | the warhead, grey, under a drawn pause mark (amber bars on a dark badge) | `programme_unfunded.dds` |
| 1 | Developing (first device) | the warhead with a brass wrench across its tail | `programme_developing.dds` |
| 2 | Producing (series production) | a rack of three warheads, one above another | `programme_producing.dds` |
| 3 | Frozen (pause treaty) | the warhead with a red wax seal on a blue ribbon | `programme_frozen.dds` |
| 4 | At ceiling | the rack of three under a flat gold bar | `programme_at_ceiling.dds` |
| 5 | Dismantling | the warhead split in two halves, a brass wrench between them | `programme_dismantling.dds` |
| 6 | No programme | the warhead, faint grey, no mark | `programme_none.dds` |
| 7 | Renounced | a pale grey dove with an olive branch over the split warhead | `programme_renounced.dds` |
| 8 | Disarmed (settlement or NPT) | the warhead, grey, under vanilla's red cross | `programme_disarmed.dds` |

## Row 1: warheads and the crisis

| Cell | Shown | Shows | File |
|---|---|---|---|
| Warheads | always | the warhead alone | `warheads.dds` |
| Crisis | while in one | the warhead on a red disc, under vanilla's warning mark | `crisis.dds` |

The credibility cell is a meter, not an icon.

The Military panel's Nuclear tab shows `warheads.dds` at 24 px beside its name (`gui/panel_military.gui`, the tab strip's fourth slot).

## Row 2: the posture (while armed)

Codes: `nd_display_doctrine_code`, `nd_display_readiness_code` and `nd_display_authority_code` (`common/script_values/nuclear_deterrence_values.txt`). Each falls back as the name blocks in `nuclear_deterrence_custom_loc.txt` do. Each cell's hover is the posture row's own tooltip.

| Axis | Code | State | Shows | File |
|---|---|---|---|---|
| Doctrine | 1 | No First Use | the warhead inside a drawn gold heater shield | `doctrine_nfu.dds` |
| Doctrine | 2 | Existential Deterrence | the warhead resting on a low wall of rough grey stone | `doctrine_existential.dds` |
| Doctrine | 3 | Flexible First Use | the warhead tilted forward, a smaller drawn gold heater shield behind it | `doctrine_flexible.dds` |
| Doctrine | 4 | Nuclear Compellence | the warhead pointing right at a red arrow | `doctrine_compellence.dds` |
| Doctrine | 5 | Nuclear Warfighting | the warhead crossed with a broad steel sword, gold hilt | `doctrine_warfighting.dds` |
| Readiness | 0 | Recessed | a closed dark-green steel crate under a brass padlock | `readiness_recessed.dds` |
| Readiness | 1 | Routine | the missile lying flat over the pad, green lamp | `readiness_routine.dds` |
| Readiness | 2 | Heightened | the missile raised about 40 degrees, amber lamp | `readiness_heightened.dds` |
| Readiness | 3 | High Alert | the missile upright on the pad, red lamp | `readiness_high_alert.dds` |
| Launch authority | 1 | Central Authorization | the key before a bronze seal with a star inside a laurel border | `authority_central.dds` |
| Launch authority | 2 | Conditional Delegation | the key beside an officer's peaked cap | `authority_delegation.dds` |
| Launch authority | 3 | Launch on Warning | the key beside a radar dish tilted up | `authority_on_warning.dds` |
| Launch authority | 4 | Automatic Retaliation | the key beside a grey computer cabinet with dials and a red lamp | `authority_automatic.dds` |

## Where the art departs from the list

The list this page used to be asked for some things the renderer would not draw, or that did not read at 36 px. What stood in (#586):
- **The warhead lies on its side.** The list had it standing nose up. FLUX laid it down in all four seeds, so Producing and At Ceiling are a rack of three rather than a row, and Compellence mirrors the warhead.
- **Developing** has the wrench but no open inspection panel, which was a speck at 36 px.
- **No First Use and Flexible First Use** have a drawn heater shield, because FLUX drew plaques and discs.
- **Compellence** points at a red arrow, not past a raised gauntlet, which read as a mug.
- **Readiness** stands the missile on a drawn steel pad. Every launcher FLUX drew was a flat truck already carrying a missile. The three angles and the green, amber and red lamps are as the list asked.
- **Conditional Delegation** puts the key beside an officer's cap. The list's gloved hands are a risk at icon size.
- Smaller changes: Unfunded's warhead has no cradle. Renounced's dove is pale grey, because white is lost in the cut-out. Existential's warhead rests on the wall, not behind it. On Warning's and Automatic's keys lie beside the dish and the cabinet, not under or in them.

## Row 3: the nuclear taboo

No icon of its own. The bar is the projection bar shared with Global Warming (play-test round 3). It has vanilla's `default_progressbar_horizontal` layers and no marker, and draws the change still to come in the bar's own fill at 40% opacity. The trend arrow is vanilla's `trend_up`, `trend_down` or `trend_nochange`, picked by `nd_disp_taboo_trend`. `NuclearIconsTest` allows these three as the only vanilla textures left in the overview.

The Forces section's survivability bar is built the same way. It draws the change in vanilla's green and red fills and marks its ceiling with a 3 px line of vanilla's `gfx/interface/backgrounds/white.dds`, tinted cream. Neither bar needs art.
