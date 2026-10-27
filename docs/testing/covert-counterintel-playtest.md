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
| `TE_SELF_CHECK BROKEN covert_exposure_lock` | A `.1`'s copies (`iw_burned_type_code` and siblings) outlived five monthly passes, longer than the event can stay open, so its `after` never ran; the watchdog has released the lock. Expected only after a revolution won while that `.1` was open. | Without a revolution behind it, `.1` closed without running `after`: remove the copies and the lock in each option as well. |

## Watching a caught operation

| Check | Expect | If it fails |
|---|---|---|
| **Catch reaches a player defender.** An AI's operation against a player with the Covert Warfare entry is caught (`te_debug_covert.7` a). | `covert_warfare.3` opens, naming the attacker and the operation; Expose is the default. | No event and a BROKEN line: take the fallback above. |
| **Let it run.** Choose it. | The attacker gets no event and its panel doesn't change. Our Agent Networks row inside the attacker appears that day and grows about 4 a month at priority 1 (more with Tradecraft), trend growing, not reaped. `.3.b`'s tooltip shows 4 and 6.4. | |
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
| **Launch preview.** Hover a hostile operation against a friend, and against a non-friend. | The friend warning appears only for the friend. | If it shows for everyone, use a `custom_tooltip` whose text is a custom-loc keyed on the trigger. |
| **AI.** Observer run. | AIs don't launch the six formerly blocked operations against friends; they still spy on friends with espionage and pay when caught. | |

## Counterintelligence Support

| Check | Expect | If it fails |
|---|---|---|
| **Launch.** Hover the action on a friend, on a non-friend, and on an ally that already has a protector. | On a friend: the target's three +8 defence lines, the phase line and the "open arrangement" line, no detection warning. On a non-friend the friend line fails; with another protector the one-protector line fails. | |
| **Notification.** | The ally gets "[us] has begun supporting our counterintelligence services." | |
| **Launch toast on a hostile operation.** An AI launches an operation against a player. | Unknown, a question from before this branch: every covert action defines an `_action_notification_desc` addressed to its target. If the target gets a toast naming the initiator, targets learn of every launch by name, which undercuts detection as a whole, and the guide's detection section needs a sentence. The Notification row above is the same mechanism. | Nothing to fix in this branch. The fix is modelling operations without pacts (spec § D, option 3). |
| **Row.** The Operations section. | Its own icon (a black glove holding up a steel shield), "Supporting Counterintelligence in X", phase, priority stepper, "Detection Risk: none" with its hover, Stand down. Stand down clears the protector mark, so another country can launch it there. | |
| **Effect.** From month 6. | The ally's covert defences rise by +8 per axis, ×2 from month 12, ×1.35 / ×1.6 at priority 2 / 3 (its modifier breakdown). | |
| **Nothing for the protector.** | No Agent Networks row for the ally; Tradecraft doesn't rise from it; with only Counterintelligence Support running, Tradecraft decays. | |
| **Logs.** | No `failed for unknown arguments`, no unknown trigger for `covert_op_is_hostile` or `has_diplomatic_pact … is_initiator = yes`. No `VFSOpen` line for the lens icon `covert_counterintel_support_action.dds`. | |
| **Protector mark survives.** One month after launch. | The ally still carries `iw_cis_protector`; a third country's launch there is still refused. | If the mark vanishes while the operation runs, `is_initiator = yes` reads the other way: walk the pacts from the protector instead (`any_scope_diplomatic_pact = { is_diplomatic_action_type = covert_counterintel_support_action first_country = <protector> … }`). |
| **Stale mark.** Annex the protector, or remove the pact by console. | Within a month the mark is gone and a new protector can launch. | |
| **Mutual protection.** A protects B. | Note whether B can protect A or the no-duplicate line blocks it. | If blocked and unwanted, give the no-duplicate check `is_initiator = yes` for this type. |
| **AI.** Observer run, a bloc leader or overlord with a weaker friend. | It proposes at most one and keeps it at priority 1. Peaceful AIs with no rivals never fund a service, so never launch it. | |
