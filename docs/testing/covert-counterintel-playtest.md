# Covert Warfare play-test checklist: watching, backlash, Counterintelligence Support

What the next play-test should look at for the 2026-10-16 covert work (spec
`docs/superpowers/archive/specs/2026-10-16-covert-counterintel-backlash-design.md`). In-game checks do not gate a merge
(CLAUDE.md, "In-game checks: self-checks and the play-test list"): the branch landed on the offline gate, and these are
the things only the game can show. Strike a fixed item through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Console harness:** `event te_debug_covert.7` (a: every foreign operation against us is caught now; b: expose every
  watched operation; c: relations +60 with every country running operations against us, so their catches count as
  spying on a friend; d: start Counterintelligence Support from us on a friend without a protector, six months in). The older harness events still
  work: `te_debug_covert.1` forces a detection.
- **Logs.** Read `debug.log`, not `error.log`. Search `TE_SELF_CHECK` for the self-checks below.

## Self-checks

| Line | Means | Fallback if BROKEN |
|---|---|---|
| `TE_SELF_CHECK OK covert_catch_decision` | A caught operation's saved scope reached the defender's decision event (`covert_warfare.3`), attacker to defender. | At the roll, write the attacker and type code on the target as variables and look the operation up in `.3`'s `immediate` (one decision open per target at a time). |
| `TE_SELF_CHECK BROKEN covert_catch_decision` | `.3` never ran for a pending catch; the operation was released for the next roll. | As above. |
| `TE_SELF_CHECK OK covert_watch_expose` | An exposure of a watched operation reached the attacker's `covert_warfare.1`, defender to attacker. | — |
| `TE_SELF_CHECK BROKEN covert_watch_expose` | An ordered exposure was sent but `.1` never ran. | `covert_watch_expose_record` flags the operation (`iw_expose_requested`), and the attacker's own monthly pass finds it and calls `covert_exposure_fire`. |
| `TE_SELF_CHECK OK covert_can_research_current` | `can_research` held for every country's current production or military research whose prerequisites it holds (`held=` countries, `can_research=` of them). Logged on the first monthly pulse with a sample. | — |
| `TE_SELF_CHECK BROKEN covert_can_research_current` | `can_research` failed for some current research with its prerequisites held. | Keep the prerequisite lines in covert tech theft (as built); delete the check. |
| `TE_SELF_CHECK OK covert_can_research_stranded` | `can_research` failed for every current research missing a prerequisite. Logged only in a save with such a country (the Byzantium 2013 autosaves: LIB, UNA); a fresh game logs nothing. With `current` also OK: generate `can_research` in place of the prerequisite lines and delete the check (`te_covert_tech_selfcheck_on_actions.txt` says how). | — |
| `TE_SELF_CHECK BROKEN covert_can_research_stranded` | `can_research` held for current research missing a prerequisite, so it doesn't check prerequisites. | Keep the prerequisite lines; delete the check. |
| `TE_SELF_CHECK BROKEN covert_exposure_lock` | A `.1`'s copies (`iw_burned_type_code` and siblings) outlived five monthly passes, longer than the event can stay open, so its `after` never ran; the watchdog has released the lock. Expected only after a revolution won while that `.1` was open. | Without a revolution behind it, `.1` closed without running `after`: remove the copies and the lock in each option as well. |

## Watching a caught operation

| Check | Expect | If it fails |
|---|---|---|
| **Catch reaches a player defender.** An AI's operation against a player with the Covert Warfare entry is caught (`te_debug_covert.7` a). | `covert_warfare.3` opens, naming the attacker and the operation; Expose is the default. | No event and a BROKEN line: take the fallback above. |
| **Let it run.** Choose it. | The attacker gets no event and its panel doesn't change. Our Agent Networks row inside the attacker appears that day and grows about 4 a month at priority 1 (more with Tradecraft), trend growing, not reaped. `.3.b`'s tooltip shows 4 and 8.0. | |
| **Expose from `.3`.** | `.1` opens on the attacker the same day; infamy, relations, Tradecraft loss and the backlash apply; `.2` reaches us (its 24-month cooldown permitting). | |
| **Lockout.** A second exposure of one attacker while its first `.1` is still open (a player attacker can leave it open for up to a month). | The second waits; `.3.a`'s tooltip shows the wait line; `.4` four days later exposes it if the first `.1` has been answered by then, otherwise the target's first monthly pass after the answer does; never two `.1` open on one attacker. | |
| **Slow answer / stall.** As a player attacker, leave a `.1` unanswered. | It opens itself at once (a one-month event), still names and burns the right operation when answered or when it expires to Acknowledge after a month; the lock holds only that long, so a stall skips at most one monthly detection roll per catch; no `TE_SELF_CHECK BROKEN covert_exposure_lock` line. | If the lock outlives the event, the watchdog's threshold (`covert_open_event_stale_passes`) is too high; if stalling is still worth it, decouple the roll from the lock (roll while locked and queue the catch). |
| **Several attackers exposed in one pass.** An AI defender exposes operations of two attackers in one monthly pass. | Each attacker's `.1` names its own operation. | If both name the same one, saved scopes bind late: fire one `.1` per effect and leave the rest ordered. |
| **AI defenders.** Observer run. | AIs hold `iw_known_ops` records and expose most within months; none watches forever (25% a month once its network reaches 75). | |
| **Stand-down.** The attacker stands a watched operation down. | The defender's record goes the same day. | |
| **Revolution.** A watching government is overthrown. | Its records are lost; a month later the operation can be caught again (`iw_known` cleared). | |
| **Pending watchdog.** `.3` answered or timed out. | No `iw_catch_pending` left; the operation can be caught again a month later; no BROKEN line. | |
| **Tooltip render.** Hover `.3`'s options. | No error.log lines (`Undefined event target iw_new_rec`, `iw_caught_op`). | |
| **`.2` wording after an exposure we ordered.** | Reads acceptably even though we had known for months. | Text only: a variant keyed on the operation having been watched. |

## Known Foreign Operations section

| Check | Expect | If it fails |
|---|---|---|
| **Rows.** While watching. | The section shows (open), one row per watched operation: the attacker's flag and name, the type's icon and name, months watched ticking monthly. Disappears with the last record. The Military panel's Covert tab shows the same. | |
| **Hover.** Row and type name. | Months, our network strength (matches the Agent Networks row), the monthly gain; the name's hover gives what the operation does to us. | |
| **Expose button.** A fresh row. | Enabled; a click fires `.4` then `.1` on the attacker (self-check OK line); the row reads "Exposure ordered" and leaves the list when the operation burns. | Greyed on a valid row: the `AddScope( 'iw_known', ScriptContainer.MakeScope )` link failed. Fallback: Expose opens an event listing the watched operations as options. |
| **Greyed states.** While `.1` is open on that attacker, and after one click. | Greyed, with the right tick/cross reasons. | |
| **Layout.** A long attacker name. | Wraps; doesn't push the flag. Row width matches the Networks rows. | |
| **Existing tooltips (pre-existing concern).** Stand down and priority steppers' hover. | Reason lines render. | They root at `JournalEntry` inside a datamodel item (gui gotcha #24); switch to `GetPlayer` as the Expose button does. |

## Domestic backlash

| Check | Expect | If it fails |
|---|---|---|
| **New game starts** with `common/political_lobby_appeasement/te_covert_appeasement.txt` present. | Normal start. | Remove the file and use `appeasement_special_events_negative`. |
| **Appeasement.** Catch an operation against a friend whose country has a pro-target lobby at home (and a subject spying on its overlord, `lobby_pro_overlord`). | The lobby's appeasement drops by −3/−5/−8 (Acknowledge) or −2/−3/−4 (Deny) by tier; its tooltip names the reason. No `Appeasement change failed` in error.log. | As above. |
| **`.1` tooltips.** Against a friend. | Infamy, relations (×1.5), then the home lines (appeasement, the scandal modifier). With no pro lobby, the "no lobby" line and the modifier. Against a non-friend, or a war-tier operation caught at war: no home lines at all. | |
| **Defender side.** A foreign operation exposed in a country with a pro-attacker lobby. | The lobby's interest groups carry "Foreign Ties Discredited" (−5/−10/−15% political strength by tier, ×1.5 if the attacker was a friend), fading. `.2` adds the public-anger paragraph. | Paragraph missing: move the two `triggered_desc` blocks from `.2`'s `desc` into its `flavor` chain. |
| **Named lobby in `.1`'s tooltips (2026-10-30).** Caught spying on a friend with a pro-target lobby at home. | The appeasement line names the lobby ("Appeasement of Pro-X Lobby changes by −5"). | No name or an error: `scope:iw_home_lobby` didn't survive from `immediate` to the click; pin the lobby in each option instead (`random_political_lobby` then `scope:` in the option body, keeping `test_covert_exposure_tiers`' guard counts). |
| **Named paragraphs in `.1` (2026-10-30).** As above, with a lobby in the target that favors us; then a non-friend; then a war-tier operation caught at war. | Friend: a home paragraph naming the lobby and its members, then one naming our friends' lobby in the target and its members. Non-friend: only the second. At war: neither. No raw `$covert_warfare.1.d$` text. | Raw `$key$` text: write the variants out in full instead of splicing. |
| **Members list (2026-10-30).** Any of the named texts (`.1`, `.2`, `.3`'s Expose). | `[…GetMembersDesc]` renders the lobby's interest groups ("Industrialists and Landowners"), reading naturally after "the". | Blank or an error in error.log (`GetMembersDesc` is proven only in vanilla's lobby notifications): drop the member clause and keep `GetName`, or pin the lobby's largest member (`ordered_lobby_member`, by clout) and name it with `gsInterestGroup`. |
| **Named lobby in `.2` and `.3` (2026-10-30).** A foreign operation caught at home, with a pro-attacker lobby. | `.3`'s Expose tooltip names the lobby and its members on a line of their own; `.2`'s public paragraph names them too. | |
| **Launch preview.** Hover a hostile operation against a friend, and against a non-friend. | The friend warning appears only for the friend. | If it shows for everyone, use a `custom_tooltip` whose text is a custom-loc keyed on the trigger. |
| **AI.** Observer run. | AIs don't launch the six formerly blocked operations against friends; they still spy on friends with espionage and pay when caught. | |

## Counterintelligence Support

| Check | Expect | If it fails |
|---|---|---|
| **Launch.** Hover the action on a friend, on a non-friend, and on an ally that already has a protector. | On a friend: the target's three +8 defence lines, the phase line and the "open arrangement" line, no detection warning. On a non-friend the friend line fails; with another protector the one-protector line fails. | |
| **Notification.** | The ally gets "[us] has begun supporting our counterintelligence services." | |
| **Launch toast on a hostile operation.** An AI launches an operation against a player. | Unknown, a question from before this branch: every covert action defines an `_action_notification_desc` addressed to its target. If the target gets a toast naming the initiator, targets learn of every launch by name, which undercuts detection as a whole, and the guide's detection section needs a sentence. The Notification row above is the same mechanism. | Nothing to fix in this branch. The fix is modelling operations without pacts (spec § D, option 3). |
| **Row.** The Operations section. | The ally's flag, its own icon (a black glove holding up a steel shield), "Counterintelligence Support in X", phase, priority stepper, "Detection Risk: none" with its hover, Stand down. Stand down clears the protector mark, so another country can launch it there. | |
| **Effect.** From month 6. | The ally's covert defences rise by +8 per axis, ×2 from month 12, ×1.65 / ×2 at priority 2 / 3 (its modifier breakdown). | |
| **Nothing for the protector.** | No Agent Networks row for the ally; Tradecraft doesn't rise from it; with only Counterintelligence Support running, Tradecraft decays. | |
| **Logs.** | No `failed for unknown arguments`, no unknown trigger for `covert_op_is_hostile` or `has_diplomatic_pact … is_initiator = yes`. No `VFSOpen` line for the lens icon `covert_counterintel_support_action.dds`. | |
| **Protector mark survives.** One month after launch. | The ally still carries `iw_cis_protector`; a third country's launch there is still refused. | If the mark vanishes while the operation runs, `is_initiator = yes` reads the other way: walk the pacts from the protector instead (`any_scope_diplomatic_pact = { is_diplomatic_action_type = covert_counterintel_support_action first_country = <protector> … }`). |
| **Stale mark.** Annex the protector, or remove the pact by console. | Within a month the mark is gone and a new protector can launch. | |
| **Mutual protection.** A protects B. | Note whether B can protect A or the no-duplicate line blocks it. | If blocked and unwanted, give the no-duplicate check `is_initiator = yes` for this type. |
| **AI.** Observer run, a bloc leader or overlord with a weaker friend. | It proposes at most one and keeps it at priority 1. Peaceful AIs with no rivals never fund a service, so never launch it. | |

## Panels after the GUI audit (COV-1 to COV-14, 2026-10-27)

The Covert tab and the journal entry after the 2026-10-27 audit (`docs/audits/gui_audit/hegemony_covert.md`). No
self-check: nothing here rests on an engine fact script can test. Run any harness above that starts operations
(`te_debug_covert.1`, `.7`), or launch two or three operations by hand.

| Check | Expect | If it fails |
|---|---|---|
| **Names (COV-3).** Launch Incite Colonial Autonomy, Secure Loose Material or Survey Colony Defenses, then read the diplomatic action, the Operations row and, on the target's side, the Known row and the events. | One name everywhere: the action's without "Covert: ". The action names read "Covert: Survey Colony Defenses" (the action splices `iw_op_name_<type>`). | A raw `$iw_op_name_...$` in the Diplomacy panel: the engine does not resolve a splice in a diplomatic action's name; type the names into `covert_<type>_action` again, and keep `test_covert_op_registry` holding them equal. |
| **The row (COV-1, COV-4, COV-12).** The Operations section. | Each row leads with the target's flag (hover names it, click opens the country), then the operation's icon and its plain title. Hovering the title lists what it does at base strength as modifier lines, and "Strength now: ×2.00, for its phase and priority". A line "Exposure: Interference" (or Routine Espionage, Attack on a Government, Wartime Sabotage) carries the cost of a catch on hover; Counterintelligence Support has none. | Blank modifier lines: `GetStaticModifier(...).GetDesc` does not render in a datamodel tooltip; fall back to the action's description text. No Exposure line after a month: `iw_exposure_tier` is not written (`covert_op_refresh_exposure_tier`). |
| **Detection breakdown (COV-5).** Hover an operation's Detection Risk line. | A table: Base, their counterintelligence (with their capacity and defenses against ours), their network inside our service, our network there, Funding Stealth, Priority and the Efficiency factor, adding up to the figure on the row (within the 0.1% floor and the 50% ceiling). On a save from before the update, one line until the next monthly review. | |
| **Bars (COV-6).** The overview's Capacity and Tradecraft bars. | Thin lines at 20 / 40 / 60 / 80% on Capacity and at each Tradecraft tier's floor, each with its own hover ("Hardened from 60% of the world's best ...", "Seasoned from 60: Regime Change, ..."). No eye-shaped marker. The Tradecraft figure reads "42 · next 60", or "85 · top tier". | A line drawn at the bar's left end: the `marker` of a transparent progressbar does not follow its value here; compare the Colonial Empire bar's next-band line. |
| **Tradecraft hover (COV-7).** Hover the Tradecraft bar. | Its score and tier, this month's operations counted, the last change, and the next tier with what it unlocks. The gain and loss rules are in How Covert Warfare Works, not here. | |
| **Buttons (COV-9).** Hover Stand down and the priority − and + on a row; step an operation from 1 to 2 and from 2 to 3 below Established Tradecraft. | No ticked "can be identified" or "is one of ours" lines. The Tradecraft line appears only on the step to 3. A greyed button says why. | |
| **Funding section (COV-11).** At funding 0, funded with nothing running, and running. | The state line shows only while funded with nothing running; at 0 the overview and the Operations banner say so. | |
| **Network table (COV-12).** Two or three networks: one below strength 50, one between 50 and 75, one above (`event te_debug_covert.5` sets strength). | One table: a head (Country, Strength, Ops, Head Start, Report), then one line a network: a small flag (hover names the country, click opens it), the name, the strength figure with a bar and an arrow, our operations there, the head start ("1 month", "3 months"), and None, Partial or Full under Report. The columns line up under the head, and the rows are as wide as the Known Foreign Operations rows. Hovering the name gives what the network adds to catching their operations; Partial and Full give the report (their capacity and technologies beside ours, and from 75 how many operations they run against us); None and the Report head say from which strength each part comes. A long name ("Czechoslovakia", "United States of America") wraps in its column without pushing the others. | A blank flag or name: the `tiny_flag` datacontext or the name's chain does not resolve inside this datamodel; the Known rows read the same chain. A cell ending in "...": widen it and re-budget it in `test_covert_layout.NetworkTableTest` / `WidthBudgetTest`. |
| **Launch tooltip (COV-2).** Hover an operation's action on a country where we have a network, and on one where we have none. | "Our network there: 45, a head start of 2 months" (or "none yet, so no head start"), "Upkeep: +X/week at priority 1, at today's funding level", the detection warning, and one phase line naming Operation Phase, whose hover has the rest. | No network line on a country with a network: the `every_in_list` in `covert_op_launch_summary` does not render in an action's tooltip, or `THIS.Var` does not read the network container there. Fall back to a network-scoped script value read through `GetPlayer`, written onto the operator for the target when the panel opens. |
| **Type sizes (COV-14).** Read every section at the new sizes. | Rows and buttons at 17, titles and subheadings at 20, the overview at 16. Nothing ends in "...": "Established" in the overview's Tradecraft cell, "5 Covert Network" in the stepper, Stand down's label. | Widen the cell, then re-budget it in `test_covert_layout.WidthBudgetTest`. |

## Technology theft and stranded research (#1244, 2026-10-30)

Espionage's current-research theft now also checks the technology's prerequisites, by name. The log line the fix
removes is its test. The `covert_can_research_*` self-checks above say whether one `can_research` line could replace
those prerequisite lines. Load the Byzantium save before #1252's repair runs, or its two stranded countries are gone.

| Check | Expect | If it fails |
|---|---|---|
| **Stranded research.** Load the Byzantium game's 2013 autosaves, where LIB and UNA research Asteroid Mining without In-Situ Resource Utilization, and run a few months. | No `You need to acquire the technology before adding progress ... covert_tech_theft_generated.txt` line in `error.log`. LIB's military espionage on BYZ steals another military technology it could research now, or ends for want of one. | The line still names a `covert_tech_grant_era_N` grant: find the thief's operation in the save (`iw_stolen_last` is the technology's number in `covert_stolen_tech_name`) and compare its `acquired_technologies` with that technology's `unlocking_technologies`. |
| **Current research still stolen.** A country researching a technology its espionage target has. | The row's latest technology is that research, month after month, until it completes. | The prerequisite lines in `covert_tech_steal_<category>` don't hold for current research: check the generated branch against the technology's `unlocking_technologies`. |

## Priority fills operation slots (2026-10-31)

An operation now fills one operation slot per level of its priority (`covert_operation_slots_used`). No self-check: the
count is a script value over `iw_ops` the way the Grand Monuments values already sum their lists. Launch two or three
operations by hand, or with `te_debug_covert.1`.

| Check | Expect | If it fails |
|---|---|---|
| **Overview.** Raise one operation to 2, then 3. | "Operation Slots: n of m in use" and the lit case files rise by one a step, on the click; the hover reads "n in use by k operations, f free". Counterintelligence's unused-slot line falls by one a step. | Icons don't move until the next month: the GUI caches the script value; nothing in script waits for the pulse. |
| **Gate.** Fill every slot, then hover + on a row. | The button is greyed with a cross on "We have a free operation slot: each level of priority fills one more". − still works and frees a slot at once; a launch is refused for want of a free slot while they're all filled. | + stays clickable: `covert_possible_priority_up` isn't reading the live count. |
| **Lost slots.** Drop a slot (`remove_modifier` on a slot source, or lose rank) with an operation at 3. | It stays at 3 and keeps running; + is greyed until a slot is free; nothing is stood down. | |
| **AI.** Observer run, then switch to a great power at war with a rival. | Its overview never shows more slots in use than it holds, unless it lost slots while its operations stood higher. | |
